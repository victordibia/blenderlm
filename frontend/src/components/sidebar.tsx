import React from "react";
import { Link } from "gatsby";
import { useConfigStore } from "../hooks/store";
import { PanelLeftClose, PanelLeftOpen, Rotate3D } from "lucide-react";
import Icon from "./icons";

interface INavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  breadcrumbs?: Array<{
    name: string;
    href: string;
    current?: boolean;
  }>;
}

const navigation: INavItem[] = [
  {
    name: "Home",
    href: "/",
    icon: Rotate3D,
    breadcrumbs: [{ name: "Blender LM", href: "/", current: true }],
  },
];

const classNames = (...classes: (string | undefined | boolean)[]) => {
  return classes.filter(Boolean).join(" ");
};

type SidebarProps = {
  link: string;
  meta?: {
    title: string;
    description: string;
  };
  isMobile: boolean;
};

const Sidebar = ({ link, meta, isMobile }: SidebarProps) => {
  const { sidebar, setHeader, setSidebarState } = useConfigStore();
  const { isExpanded } = sidebar;

  // Set initial header state based on current route
  React.useEffect(() => {
    setNavigationHeader(link);
  }, [link]);

  // Always show full sidebar in mobile view
  const showFull = isMobile || isExpanded;

  const handleNavClick = (item: INavItem) => {
    // if (!isExpanded) {
    //   setSidebarState({ isExpanded: true });
    // }
    setHeader({
      title: item.name,
      breadcrumbs: item.breadcrumbs,
    });
  };

  const setNavigationHeader = (path: string) => {
    const navItem = navigation.find((item) => item.href === path);
    if (navItem) {
      setHeader({
        title: navItem.name,
        breadcrumbs: navItem.breadcrumbs,
      });
    } else if (path === "/settings") {
      setHeader({
        title: "Settings",
        breadcrumbs: [{ name: "Settings", href: "/settings", current: true }],
      });
    }
  };

  return (
    <div
      className={classNames(
        "flex grow   z-50  flex-col gap-y-5 overflow-y-auto border-r border-secondary bg-primary",
        "transition-all duration-300 ease-in-out",
        showFull ? "w-72 px-6" : "w-16 px-2"
      )}
    >
      {/* App Logo/Title */}
      <div
        className={classNames(
          "flex h-16 items-center",
          showFull ? "gap-x-3" : "justify-center"
        )}
      >
        <Link
          to="/"
          onClick={() => setNavigationHeader("/")}
          className={classNames(
            "text-accent hover:opacity-80 transition-opacity",
            showFull ? "w-8 text-right" : "w-auto"
          )}
        >
          <Icon icon="app" size={8} />
        </Link>
        {showFull && (
          <div className="flex flex-col">
            <span className="text-base font-semibold text-primary">
              {meta?.title}
            </span>
            <span className="text-xs text-secondary">{meta?.description}</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col">
        <ul role="list" className="flex flex-1 flex-col gap-y-7">
          {/* Main Navigation */}
          <li>
            <ul
              role="list"
              className={classNames(
                "-mx-2 space-y-1",
                !showFull && "items-center"
              )}
            >
              {navigation.map((item) => {
                const isActive = item.href === link;
                const IconComponent = item.icon;

                const navLink = (
                  <div className="relative">
                    {isActive && (
                      <div className="bg-accent absolute top-1 left-0.5 z-50 h-8 w-1 bg-opacity-80  rounded">
                        {" "}
                      </div>
                    )}
                    <Link
                      to={item.href}
                      onClick={() => handleNavClick(item)}
                      className={classNames(
                        // Base styles
                        "group flex rounded-md p-2 text-sm font-medium",
                        !showFull ? "justify-center mx-auto" : "gap-x-3",
                        // Color states
                        isActive
                          ? "bg-secondary text-primary "
                          : "text-secondary hover:bg-tertiary hover:text-accent"
                      )}
                    >
                      <IconComponent
                        className={classNames(
                          "h-6 w-6 shrink-0",
                          isActive
                            ? "text-accent"
                            : "text-secondary group-hover:text-accent"
                        )}
                      />
                      {showFull && item.name}
                    </Link>
                  </div>
                );

                return <li key={item.name}>{navLink}</li>;
              })}
            </ul>
          </li>

          {/* Settings at bottom */}
          <li
            className={classNames(
              "mt-auto mb-4",
              showFull ? "-mx-2" : "flex flex-col items-center gap-2 mx-auto"
            )}
          >
            <div
              className={classNames(
                "flex items-center",
                showFull ? "gap-2" : "flex-col"
              )}
            >
              {/* <Link
                to="/settings"
                onClick={() =>
                  setHeader({
                    title: "Settings",
                    breadcrumbs: [
                      {
                        name: "Settings",
                        href: "/settings",
                        current: true,
                      },
                    ],
                  })
                }
                className={classNames(
                  "group flex items-center rounded-md p-2 text-sm font-medium text-primary hover:text-accent hover:bg-secondary",
                  showFull ? "gap-x-3" : "justify-center w-full"
                )}
              >
                <Settings className="h-6 w-6 shrink-0 text-secondary group-hover:text-accent" />
                {showFull && "Settings"}
              </Link> */}
              {!isMobile && (
                <button
                  onClick={() => setSidebarState({ isExpanded: !isExpanded })}
                  className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
                >
                  {isExpanded ? (
                    <PanelLeftClose strokeWidth={1.5} className="h-6 w-6" />
                  ) : (
                    <PanelLeftOpen strokeWidth={1.5} className="h-6 w-6" />
                  )}
                </button>
              )}
            </div>
          </li>
        </ul>
      </nav>
    </div>
  );
};

export default Sidebar;
