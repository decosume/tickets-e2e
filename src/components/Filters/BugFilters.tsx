import React from 'react';
import { Card, Form, Select, Input, Row, Col, Button } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import styled from 'styled-components';

const StyledCard = styled(Card)`
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

interface BugFiltersProps {
  onFilterChange: (filters: any) => void;
  onReset: () => void;
}

const BugFilters: React.FC<BugFiltersProps> = ({ onFilterChange, onReset }) => {
  const [form] = Form.useForm();

  const handleValuesChange = (changedValues: any, allValues: any) => {
    onFilterChange(allValues);
  };

  const handleReset = () => {
    form.resetFields();
    onReset();
  };

  return (
    <StyledCard title="Filters">
      <Form
        form={form}
        layout="vertical"
        onValuesChange={handleValuesChange}
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Form.Item name="sourceSystem" label="Source System">
              <Select
                placeholder="All Sources"
                allowClear
                options={[
                  { label: 'Slack', value: 'slack' },
                  { label: 'Shortcut', value: 'shortcut' },
                  { label: 'Zendesk', value: 'zendesk' },
                ]}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Form.Item name="priority" label="Priority">
              <Select
                placeholder="All Priorities"
                allowClear
                options={[
                  { label: 'High', value: 'high' },
                  { label: 'Medium', value: 'medium' },
                  { label: 'Low', value: 'low' },
                  { label: 'Unknown', value: 'Unknown' },
                ]}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Form.Item name="state" label="State">
              <Select
                placeholder="All States"
                allowClear
                options={[
                  { label: 'Open', value: 'open' },
                  { label: 'Closed', value: 'closed' },
                  { label: 'In Progress', value: 'in_progress' },
                  { label: 'Unknown', value: 'Unknown' },
                ]}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Form.Item name="search" label="Search">
              <Input
                placeholder="Search bugs..."
                prefix={<SearchOutlined />}
                allowClear
              />
            </Form.Item>
          </Col>
        </Row>
        <Row>
          <Col>
            <Button
              type="default"
              icon={<ReloadOutlined />}
              onClick={handleReset}
            >
              Reset Filters
            </Button>
          </Col>
        </Row>
      </Form>
    </StyledCard>
  );
};

export default BugFilters;


