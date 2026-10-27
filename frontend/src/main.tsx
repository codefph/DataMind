import React from "react";
import ReactDOM from "react-dom/client";
import { App as AntdApp, ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "antd/dist/reset.css";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#2457c5",
          colorInfo: "#2457c5",
          colorSuccess: "#16856b",
          colorWarning: "#c27a18",
          colorError: "#c44747",
          borderRadius: 10,
          fontFamily:
            '"IBM Plex Sans", "Inter", "PingFang SC", "Microsoft YaHei", sans-serif',
          controlHeight: 38,
        },
      }}
    >
      <AntdApp>
        <App />
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
);
