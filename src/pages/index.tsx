import React, { useState, useEffect } from 'react';
import { Layout, Typography, Row, Col, Spin, Alert } from 'antd';
import { BugOutlined } from '@ant-design/icons';
import styled from 'styled-components';
import DashboardStats from '../components/Dashboard/DashboardStats';
import SourceChart from '../components/Charts/SourceChart';
import BugFilters from '../components/Filters/BugFilters';
import BugList from '../components/BugList/BugList';
import { bugTrackerAPI, DashboardStats as StatsType, Bug, BugFilters as FiltersType } from '../lib/api';

const { Header, Content } = Layout;
const { Title } = Typography;

const StyledLayout = styled(Layout)`
  min-height: 100vh;
  background: #f0f2f5;
`;

const StyledHeader = styled(Header)`
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  padding: 0 24px;
`;

const StyledContent = styled(Content)`
  padding: 24px;
`;

const StyledTitle = styled(Title)`
  margin: 0 !important;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<StatsType | null>(null);
  const [bugs, setBugs] = useState<Bug[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FiltersType>({});

  // Load dashboard data
  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load stats and bugs in parallel
      const [statsData, bugsData] = await Promise.all([
        bugTrackerAPI.getStats(),
        bugTrackerAPI.getBugs(filters)
      ]);

      setStats(statsData);
      setBugs(bugsData);
    } catch (err) {
      console.error('Error loading dashboard:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  // Load data on component mount
  useEffect(() => {
    loadDashboard();
  }, []);

  // Reload data when filters change
  useEffect(() => {
    if (Object.keys(filters).length > 0) {
      loadDashboard();
    }
  }, [filters]);

  // Handle filter changes
  const handleFilterChange = (newFilters: FiltersType) => {
    setFilters(newFilters);
  };

  // Handle filter reset
  const handleFilterReset = () => {
    setFilters({});
  };

  // Prepare chart data
  const chartData = stats ? [
    { source: 'Slack', count: stats.bySource.slack },
    { source: 'Shortcut', count: stats.bySource.shortcut },
    { source: 'Zendesk', count: stats.bySource.zendesk }
  ] : [];

  if (loading && !stats) {
    return (
      <StyledLayout>
        <StyledContent>
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
            <div style={{ marginTop: '16px' }}>Loading dashboard...</div>
          </div>
        </StyledContent>
      </StyledLayout>
    );
  }

  return (
    <StyledLayout>
      <StyledHeader>
        <StyledTitle level={2}>
          <BugOutlined style={{ color: '#1890ff' }} />
          Unified BugTracker Dashboard
        </StyledTitle>
      </StyledHeader>

      <StyledContent>
        {error && (
          <Alert
            message="Error"
            description={error}
            type="error"
            showIcon
            closable
            style={{ marginBottom: '24px' }}
          />
        )}

        {/* Statistics Cards */}
        {stats && <DashboardStats stats={stats} />}

        <Row gutter={[24, 24]} style={{ marginTop: '24px' }}>
          {/* Charts */}
          <Col xs={24} lg={12}>
            <SourceChart data={chartData} />
          </Col>

          {/* Filters */}
          <Col xs={24} lg={12}>
            <BugFilters
              onFilterChange={handleFilterChange}
              onReset={handleFilterReset}
            />
          </Col>
        </Row>

        {/* Bug List */}
        <Row style={{ marginTop: '24px' }}>
          <Col span={24}>
            <BugList bugs={bugs} loading={loading} />
          </Col>
        </Row>
      </StyledContent>
    </StyledLayout>
  );
};

export default Dashboard;


