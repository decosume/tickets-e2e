/**
 * Real-time WebSocket client for bug tracker dashboard
 * Handles live updates, notifications, and connection management
 */

class BugTrackerRealTime {
    constructor(options = {}) {
        this.wsUrl = options.wsUrl || 'wss://your-websocket-api.execute-api.region.amazonaws.com/stage';
        this.reconnectInterval = options.reconnectInterval || 5000;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
        this.reconnectAttempts = 0;
        this.subscriptions = new Set();
        this.eventHandlers = new Map();
        this.connectionId = null;
        this.isConnected = false;
        
        this.init();
    }

    init() {
        this.connect();
        this.setupEventListeners();
    }

    connect() {
        try {
            this.ws = new WebSocket(this.wsUrl);
            this.setupWebSocketHandlers();
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.scheduleReconnect();
        }
    }

    setupWebSocketHandlers() {
        this.ws.onopen = (event) => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.connectionId = this.generateConnectionId();
            
            // Restore subscriptions after reconnect
            this.restoreSubscriptions();
            
            // Notify listeners
            this.emit('connected', { connectionId: this.connectionId });
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        this.ws.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            this.isConnected = false;
            this.connectionId = null;
            
            if (!event.wasClean) {
                this.scheduleReconnect();
            }
            
            this.emit('disconnected', { code: event.code, reason: event.reason });
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', error);
        };
    }

    handleMessage(message) {
        const { type, ...data } = message;
        
        switch (type) {
            case 'subscription_confirmed':
                console.log('Subscription confirmed:', data.subscription);
                this.emit('subscription_confirmed', data);
                break;
                
            case 'bug_created':
                this.handleBugCreated(data.bug);
                break;
                
            case 'bug_updated':
                this.handleBugUpdated(data.bug);
                break;
                
            case 'bug_resolved':
                this.handleBugResolved(data.bug);
                break;
                
            default:
                console.log('Unknown message type:', type, data);
        }
        
        // Emit generic message event
        this.emit('message', message);
    }

    handleBugCreated(bug) {
        console.log('New bug created:', bug);
        
        // Update dashboard
        this.updateDashboard('create', bug);
        
        // Show notification
        this.showNotification({
            type: 'info',
            title: 'New Bug Reported',
            message: `${bug.source_system}: ${bug.subject}`,
            bug: bug
        });
        
        this.emit('bug_created', bug);
    }

    handleBugUpdated(bug) {
        console.log('Bug updated:', bug);
        
        // Update dashboard
        this.updateDashboard('update', bug);
        
        // Show notification for high priority updates
        if (bug.priority === 'Critical' || bug.priority === 'High') {
            this.showNotification({
                type: 'warning',
                title: 'High Priority Bug Updated',
                message: `${bug.subject} - Status: ${bug.status}`,
                bug: bug
            });
        }
        
        this.emit('bug_updated', bug);
    }

    handleBugResolved(bug) {
        console.log('Bug resolved:', bug);
        
        // Update dashboard
        this.updateDashboard('resolve', bug);
        
        // Show success notification
        this.showNotification({
            type: 'success',
            title: 'Bug Resolved',
            message: `${bug.subject} has been resolved`,
            bug: bug
        });
        
        this.emit('bug_resolved', bug);
    }

    updateDashboard(action, bug) {
        // Update bug list if visible
        const bugList = document.querySelector('.bug-list');
        if (bugList) {
            this.updateBugList(action, bug);
        }
        
        // Update summary statistics
        this.updateSummaryStats(action, bug);
        
        // Update charts
        this.updateCharts(action, bug);
    }

    updateBugList(action, bug) {
        const bugList = document.querySelector('.bug-list tbody');
        if (!bugList) return;
        
        const existingRow = document.querySelector(`[data-bug-id="${bug.PK}"]`);
        
        if (action === 'create') {
            // Add new row at the top
            const newRow = this.createBugRow(bug);
            newRow.classList.add('new-bug-highlight');
            bugList.insertBefore(newRow, bugList.firstChild);
            
            // Remove highlight after animation
            setTimeout(() => {
                newRow.classList.remove('new-bug-highlight');
            }, 3000);
            
        } else if (action === 'update' && existingRow) {
            // Update existing row
            const updatedRow = this.createBugRow(bug);
            updatedRow.classList.add('updated-bug-highlight');
            existingRow.replaceWith(updatedRow);
            
            // Remove highlight after animation
            setTimeout(() => {
                updatedRow.classList.remove('updated-bug-highlight');
            }, 2000);
            
        } else if (action === 'resolve' && existingRow) {
            // Mark as resolved and fade out if not showing resolved bugs
            existingRow.classList.add('resolved-bug');
            if (!this.shouldShowResolvedBugs()) {
                setTimeout(() => {
                    existingRow.remove();
                }, 1000);
            }
        }
    }

    updateSummaryStats(action, bug) {
        const summaryElements = {
            total: document.querySelector('.total-bugs .stat-value'),
            high: document.querySelector('.high-priority .stat-value'),
            inProgress: document.querySelector('.in-progress .stat-value'),
            resolved: document.querySelector('.resolved .stat-value')
        };
        
        // Update counters based on action
        if (action === 'create') {
            this.incrementCounter(summaryElements.total);
            if (bug.priority === 'High' || bug.priority === 'Critical') {
                this.incrementCounter(summaryElements.high);
            }
        } else if (action === 'resolve') {
            this.incrementCounter(summaryElements.resolved);
            if (bug.status === 'In Progress') {
                this.decrementCounter(summaryElements.inProgress);
            }
        }
    }

    subscribe(subscriptionType, filters = {}) {
        if (!this.isConnected) {
            console.warn('WebSocket not connected. Subscription will be applied when connected.');
            this.subscriptions.add({ type: subscriptionType, filters });
            return;
        }
        
        const subscription = {
            action: 'subscribe',
            type: subscriptionType,
            filters: filters
        };
        
        this.ws.send(JSON.stringify(subscription));
        this.subscriptions.add(subscription);
    }

    unsubscribe(subscriptionType) {
        // Remove from local subscriptions
        this.subscriptions = new Set([...this.subscriptions].filter(
            sub => sub.type !== subscriptionType
        ));
        
        // Send unsubscribe message if connected
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                action: 'unsubscribe',
                type: subscriptionType
            }));
        }
    }

    // Event system
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        this.eventHandlers.get(event).add(handler);
    }

    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).delete(handler);
        }
    }

    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }

    // Utility methods
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.emit('max_reconnects_reached');
            return;
        }
        
        this.reconnectAttempts++;
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectInterval * this.reconnectAttempts);
    }

    restoreSubscriptions() {
        this.subscriptions.forEach(subscription => {
            this.ws.send(JSON.stringify(subscription));
        });
    }

    showNotification(notification) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `notification toast ${notification.type}`;
        toast.innerHTML = `
            <div class="notification-content">
                <strong>${notification.title}</strong>
                <p>${notification.message}</p>
            </div>
            <button class="close-btn">&times;</button>
        `;
        
        // Add to page
        const container = document.querySelector('.notifications-container') || 
                         document.body;
        container.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
        
        // Close button handler
        toast.querySelector('.close-btn').onclick = () => toast.remove();
    }

    createBugRow(bug) {
        const row = document.createElement('tr');
        row.setAttribute('data-bug-id', bug.PK);
        row.innerHTML = `
            <td><a href="#" class="bug-link">${bug.PK}</a></td>
            <td><span class="source-badge ${bug.source_system}">${bug.source_system}</span></td>
            <td class="bug-subject">${bug.subject}</td>
            <td><span class="priority-badge ${bug.priority?.toLowerCase()}">${bug.priority}</span></td>
            <td><span class="status-badge ${bug.status?.toLowerCase()?.replace(' ', '-')}">${bug.status}</span></td>
            <td>${bug.assignee || 'Unassigned'}</td>
            <td>${new Date(bug.createdAt).toLocaleDateString()}</td>
            <td class="actions">
                <button class="btn-sm view-btn">👁️</button>
                <button class="btn-sm edit-btn">✏️</button>
            </td>
        `;
        return row;
    }

    generateConnectionId() {
        return `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    incrementCounter(element) {
        if (element) {
            const current = parseInt(element.textContent) || 0;
            element.textContent = current + 1;
            element.classList.add('stat-updated');
            setTimeout(() => element.classList.remove('stat-updated'), 1000);
        }
    }

    decrementCounter(element) {
        if (element) {
            const current = parseInt(element.textContent) || 0;
            element.textContent = Math.max(0, current - 1);
            element.classList.add('stat-updated');
            setTimeout(() => element.classList.remove('stat-updated'), 1000);
        }
    }

    shouldShowResolvedBugs() {
        // Check current filter settings
        const statusFilter = document.querySelector('#status-filter');
        return statusFilter?.value === 'all' || statusFilter?.value === 'resolved';
    }

    setupEventListeners() {
        // Page visibility API to handle reconnection when tab becomes visible
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !this.isConnected) {
                this.connect();
            }
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (this.ws) {
                this.ws.close(1000, 'Page unloading');
            }
        });
    }

    disconnect() {
        if (this.ws) {
            this.ws.close(1000, 'User disconnected');
        }
    }
}

// Usage example:
window.addEventListener('DOMContentLoaded', () => {
    const realtime = new BugTrackerRealTime({
        wsUrl: 'wss://your-websocket-api.execute-api.us-west-2.amazonaws.com/prod'
    });
    
    // Subscribe to all updates
    realtime.subscribe('all');
    
    // Subscribe to high priority bugs only
    // realtime.subscribe('priority', { priorities: ['Critical', 'High'] });
    
    // Subscribe to specific sources
    // realtime.subscribe('source', { sources: ['zendesk', 'shortcut'] });
    
    // Event handlers
    realtime.on('connected', () => {
        console.log('Real-time updates enabled');
        document.querySelector('.connection-status').textContent = 'Connected';
    });
    
    realtime.on('disconnected', () => {
        console.log('Real-time updates disabled');
        document.querySelector('.connection-status').textContent = 'Disconnected';
    });
    
    // Make available globally
    window.bugTrackerRealTime = realtime;
});
