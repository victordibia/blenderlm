import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import MainViewManager from "../components/views/main/manager";

// markup
const IndexPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Home" link={"/"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <MainViewManager />
      </main>
    </Layout>
  );
};

export const query = graphql`
  query HomePageQuery {
    site {
      siteMetadata {
        description
        title
      }
    }
  }
`;

export default IndexPage;
