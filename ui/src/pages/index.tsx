import * as React from "react";
import type { HeadFC, PageProps } from "gatsby";
import MainView from "../components/views/main";
import "../styles/global.css";

const IndexPage: React.FC<PageProps> = () => {
  return <MainView />;
};

export default IndexPage;

export const Head: HeadFC = () => <title>Home Page</title>;
