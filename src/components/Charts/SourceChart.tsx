import React from 'react';
import { Card } from 'antd';
import { Pie } from '@ant-design/plots';
import styled from 'styled-components';

const StyledCard = styled(Card)`
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

interface SourceChartProps {
  data: Array<{
    source: string;
    count: number;
  }>;
}

const SourceChart: React.FC<SourceChartProps> = ({ data }) => {
  const config = {
    data,
    angleField: 'count',
    colorField: 'source',
    radius: 0.8,
    label: {
      type: 'outer',
      content: '{name} {percentage}',
    },
    interactions: [
      {
        type: 'element-active',
      },
    ],
    color: ['#4A154B', '#FF6B35', '#03363D'],
  };

  return (
    <StyledCard title="Bugs by Source System">
      <Pie {...config} />
    </StyledCard>
  );
};

export default SourceChart;


