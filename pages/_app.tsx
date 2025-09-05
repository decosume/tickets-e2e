import type { AppProps } from 'next/app';
import { ConfigProvider } from 'antd';
import { createGlobalStyle } from 'styled-components';

const GlobalStyle = createGlobalStyle`
  * {
    box-sizing: border-box;
  }

  html,
  body {
    padding: 0;
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen,
      Ubuntu, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;
  }

  a {
    color: inherit;
    text-decoration: none;
  }

  /* Ant Design overrides */
  .ant-layout {
    background: #f0f2f5;
  }

  .ant-card {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .ant-statistic-title {
    font-size: 14px;
    color: #666;
  }

  .ant-statistic-content {
    font-size: 24px;
    font-weight: 600;
  }
`;

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <GlobalStyle />
      <Component {...pageProps} />
    </ConfigProvider>
  );
}


