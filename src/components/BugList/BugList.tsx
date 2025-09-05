import React from 'react';
import { Card, List, Tag, Typography, Space, Avatar } from 'antd';
import { BugOutlined, MessageOutlined, ProjectOutlined, CustomerServiceOutlined } from '@ant-design/icons';
import styled from 'styled-components';

const { Text, Paragraph } = Typography;

const StyledCard = styled(Card)`
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

const StyledListItem = styled(List.Item)`
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.3s ease;
  
  &:hover {
    background-color: #f5f5f5;
    transform: translateX(4px);
  }
`;

interface Bug {
  id: string;
  sourceSystem: string;
  priority: string;
  state: string;
  name: string;
  description?: string;
  author?: string;
  createdAt: string;
  updatedAt: string;
}

interface BugListProps {
  bugs: Bug[];
  loading?: boolean;
}

const BugList: React.FC<BugListProps> = ({ bugs, loading = false }) => {
  const getSourceIcon = (sourceSystem: string) => {
    switch (sourceSystem) {
      case 'slack':
        return <MessageOutlined style={{ color: '#4A154B' }} />;
      case 'shortcut':
        return <ProjectOutlined style={{ color: '#FF6B35' }} />;
      case 'zendesk':
        return <CustomerServiceOutlined style={{ color: '#03363D' }} />;
      default:
        return <BugOutlined />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      case 'low':
        return 'green';
      default:
        return 'default';
    }
  };

  const getStateColor = (state: string) => {
    switch (state.toLowerCase()) {
      case 'open':
        return 'blue';
      case 'closed':
        return 'green';
      case 'in_progress':
        return 'orange';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <StyledCard title={`Recent Bugs (${bugs.length})`}>
      <List
        loading={loading}
        dataSource={bugs}
        renderItem={(bug) => (
          <StyledListItem>
            <List.Item.Meta
              avatar={
                <Avatar icon={getSourceIcon(bug.sourceSystem)} />
              }
              title={
                <Space>
                  <Text strong>{bug.name}</Text>
                  <Tag color={getPriorityColor(bug.priority)}>
                    {bug.priority}
                  </Tag>
                  <Tag color={getStateColor(bug.state)}>
                    {bug.state}
                  </Tag>
                </Space>
              }
              description={
                <Space direction="vertical" size="small">
                  <Text type="secondary">
                    ID: {bug.id} | Created: {formatDate(bug.createdAt)}
                  </Text>
                  {bug.description && (
                    <Paragraph ellipsis={{ rows: 2 }}>
                      {bug.description}
                    </Paragraph>
                  )}
                  {bug.author && (
                    <Text type="secondary">
                      Author: {bug.author}
                    </Text>
                  )}
                </Space>
              }
            />
          </StyledListItem>
        )}
      />
    </StyledCard>
  );
};

export default BugList;


