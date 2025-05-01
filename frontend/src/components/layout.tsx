import * as React from "react";
import { X } from "lucide-react";
import { appContext } from "../hooks/provider";
import { useConfigStore } from "../hooks/store";
import Footer from "./footer";
import "antd/dist/reset.css";
import SideBar from "./sidebar";
import ContentHeader from "./contentheader";
import { ConfigProvider, theme, Drawer } from "antd";
import { useAuth } from "../auth/context";
import ProtectedRoute from "../auth/protected";

const classNames = (...classes: (string | undefined | boolean)[]) => {
  return classes.filter(Boolean).join(" ");
};

type Props = {
  title: string;
  link: string;
  children?: React.ReactNode;
  showHeader?: boolean;
  restricted?: boolean;
  meta?: any;
};

const Layout = ({
  meta,
  title,
  link,
  children,
  showHeader = true,
  restricted = true,
}: Props) => {
  const { darkMode } = React.useContext(appContext);
  const { sidebar } = useConfigStore();
  const { isExpanded } = sidebar;
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const { authType } = useAuth();

  // Close mobile menu on route change
  React.useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [link]);

  React.useEffect(() => {
    document.getElementsByTagName("html")[0].className = `${
      darkMode === "dark" ? "dark bg-primary" : "light bg-primary"
    }`;
  }, [darkMode]);

  const layoutContent = (
    <div className="min-h-screen flex">
      {/* Mobile menu using Antd Drawer instead of Dialog */}
      <Drawer
        placement="left"
        open={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
        closable={false}
        width="max-w-xs"
        className="md:hidden"
        contentWrapperStyle={{ maxWidth: "calc(100% - 4rem)" }}
        bodyStyle={{ padding: 0 }}
        maskStyle={{ backgroundColor: "rgba(0, 0, 0, 0.3)" }}
      >
        <div className="absolute right-0 top-0 flex w-16 justify-center pt-5 z-10">
          <button
            type="button"
            className="text-secondary"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <span className="sr-only">Close sidebar</span>
            <X className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>
        <SideBar link={link} meta={meta} isMobile={true} />
      </Drawer>

      {/* Desktop sidebar */}
      <div className="hidden md:flex md:flex-col md:fixed md:inset-y-0">
        <SideBar link={link} meta={meta} isMobile={false} />
      </div>

      {/* Content area */}
      <div
        className={classNames(
          "flex-1 flex flex-col min-h-screen",
          "transition-all duration-300 ease-in-out",
          "md:pl-16",
          isExpanded ? "md:pl-72" : "md:pl-16"
        )}
      >
        {showHeader && (
          <ContentHeader
            isMobileMenuOpen={isMobileMenuOpen}
            onMobileMenuToggle={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          />
        )}

        <ConfigProvider
          theme={{
            token: {
              borderRadius: 4,
              colorBgBase: darkMode === "dark" ? "#05080C" : "#ffffff",
            },
            algorithm:
              darkMode === "dark"
                ? theme.darkAlgorithm
                : theme.defaultAlgorithm,
          }}
        >
          <main className="flex-1 p-2 text-primary">{children}</main>
        </ConfigProvider>

        <Footer />
      </div>
    </div>
  );

  // If page is restricted and auth is not 'none', wrap with ProtectedRoute
  console.log("Auth Type:", authType);
  if (restricted && authType !== "none" && authType !== undefined) {
    // Check if authType is 'none' or 'basic'
    return <ProtectedRoute>{layoutContent}</ProtectedRoute>;
  }

  // Otherwise, render without protection
  return layoutContent;
};

export default Layout;
