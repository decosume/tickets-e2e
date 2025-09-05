import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import { BugOutlined, MessageOutlined, ProjectOutlined, CustomerServiceOutlined } from '@ant-design/icons';
import styled from 'styled-components';

const StyledCard = styled(Card)`
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  }
`;

interface DashboardStatsProps {
  stats: {
    total: number;
    bySource: {
      slack: number;
      shortcut: number;
      zendesk: number;
    };
  };
}

const DashboardStats: React.FC<DashboardStatsProps> = ({ stats }) => {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} lg={6}>
        <StyledCard>
          <Statistic
            title="Total Bugs"
            value={stats.total}
            prefix={<BugOutlined style={{ color: '#1890ff' }} />}
            valueStyle={{ color: '#1890ff' }}
          />
        </StyledCard>
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <StyledCard>
          <Statistic
            title="Slack Messages"
            value={stats.bySource.slack}
            prefix={<MessageOutlined style={{ color: '#4A154B' }} />}
            valueStyle={{ color: '#4A154B' }}
          />
        </StyledCard>
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <StyledCard>
          <Statistic
            title="Shortcut Stories"
            value={stats.bySource.shortcut}
            prefix={<ProjectOutlined style={{ color: '#FF6B35' }} />}
            valueStyle={{ color: '#FF6B35' }}
          />
        </StyledCard>
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <StyledCard>
          <Statistic
            title="Zendesk Tickets"
            value={stats.bySource.zendesk}
            prefix={<CustomerServiceOutlined style={{ color: '#03363D' }} />}
            valueStyle={{ color: '#03363D' }}
          />
        </StyledCard>
      </Col>
    </Row>
  );
};

export default DashboardStats;


