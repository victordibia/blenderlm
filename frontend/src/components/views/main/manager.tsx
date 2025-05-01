import React from "react";
import { TriangleAlert } from "lucide-react";
import ManualControlLab from "./labs/manualcontrol";

export const MainViewManager: React.FC = () => {
  return (
    <div className="relative flex h-full w-full">
      {/* Main Content */}
      <div className="flex-1 w-full">
        <div className="p-4 pt-2">
          {/* Header */}
          {/* <div className="flex items-center gap-2 mb-4 text-sm">
            <span className="text-primary font-medium">Labs</span>
            <span className="text-secondary">Manual Control</span>
          </div> */}

          {/* Content Area - Direct Manual Control */}
          <ManualControlLab />
        </div>
      </div>
    </div>
  );
};

export default MainViewManager;
