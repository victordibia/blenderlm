import React from "react";
import {
  RefreshCcw,
  Camera,
  AlertCircle,
  Download,
  Maximize,
  Minimize,
  Image,
} from "lucide-react";
import { ConnectionStatus } from "../../../utils/blenderapi";

interface ViewportPanelProps {
  connectionStatus: ConnectionStatus;
  previewImage: string | null;
  renderedImage: string | null; // Added prop for rendered image
  activeImageSource: "viewport" | "render"; // Added prop for tracking image source
  isViewportMinimized: boolean;
  isRefreshingViewport: boolean;
  refreshViewport: () => void;
  downloadImage: () => void;
  setIsViewportMinimized: (minimized: boolean) => void;
  errorMessage?: string; // New prop for error messages
}

const ViewportPanel: React.FC<ViewportPanelProps> = ({
  connectionStatus,
  previewImage,
  renderedImage,
  activeImageSource,
  isViewportMinimized,
  isRefreshingViewport,
  refreshViewport,
  downloadImage,
  setIsViewportMinimized,
  errorMessage,
}) => {
  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-medium text-lg flex items-center gap-2">
          {activeImageSource === "render" ? (
            <>
              <Image className="h-5 w-5 text-accent" />
              Render Result
            </>
          ) : (
            <>
              <Camera className="h-5 w-5 text-accent" />
              Blender Viewport
            </>
          )}
        </h3>

        <div className="flex items-center gap-2">
          {/* Only show refresh button when in viewport mode */}
          {activeImageSource === "viewport" && (
            <button
              className="flex items-center gap-1 px-3 py-1 bg-accent/10 hover:bg-accent/20 text-accent rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={refreshViewport}
              disabled={isRefreshingViewport || !connectionStatus.connected}
            >
              {isRefreshingViewport ? (
                <RefreshCcw className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCcw className="h-4 w-4" />
              )}
              Refresh
            </button>
          )}

          <button
            className="flex items-center justify-center h-8 w-8 bg-primary/5 hover:bg-primary/10 text-primary/70 rounded-md"
            onClick={() => setIsViewportMinimized(!isViewportMinimized)}
          >
            {isViewportMinimized ? (
              <Maximize className="h-4 w-4" />
            ) : (
              <Minimize className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      <div
        className={`flex-grow   overflow-hidden bg-primary/5 ${
          isViewportMinimized ? "h-16" : "min-h-[300px]"
        } transition-all duration-300`}
      >
        {isViewportMinimized ? (
          <div className="h-full flex items-center justify-center text-primary/50">
            <span className="text-sm">
              {activeImageSource === "render" ? "Render" : "Viewport"} minimized
            </span>
          </div>
        ) : !connectionStatus.connected ? (
          <div className="h-full flex flex-col items-center justify-center p-4">
            <AlertCircle className="h-10 w-10 text-red-500 mb-2" />
            <p className="text-primary/70 text-center mb-1">
              Not connected to Blender
            </p>
            <p className="text-primary/50 text-sm text-center max-w-md">
              Please ensure Blender is running and the BlenderLM add-on is
              installed, then check the connection status.
            </p>
          </div>
        ) : previewImage ? (
          <div className="relative h-full flex items-start  ">
            <img
              src={previewImage}
              alt={
                activeImageSource === "render"
                  ? "Blender Render"
                  : "Blender Viewport"
              }
              className="max-w-full max-h-full object-contain rounded"
              style={{ width: "auto", height: "auto" }} // Ensure image maintains exact dimensions
            />
            <button
              className="absolute top-2 right-2 bg-secondary p-2 rounded-full shadow-md hover:bg-primary/10"
              onClick={downloadImage}
            >
              <Download className="h-5 w-5 text-primary/70" />
            </button>
          </div>
        ) : errorMessage ? (
          <div className="h-full flex flex-col items-center justify-center p-4">
            <AlertCircle className="h-10 w-10 text-red-500 mb-3" />
            <p className="text-red-600 font-medium text-center mb-1">
              Error: {errorMessage}
            </p>
            {activeImageSource === "render" &&
              errorMessage.includes("no camera") && (
                <div className="mt-3 max-w-md">
                  <p className="text-primary/70 text-sm text-center mb-3">
                    To fix this error, you need to add a camera to your scene.
                  </p>
                  <div className="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 p-3 rounded-md text-xs font-mono border dark:border-gray-700">
                    import bpy
                    <br />
                    <br />
                    # Add a camera
                    <br />
                    bpy.ops.object.camera_add(location=(7, -7, 5))
                    <br />
                    cam = bpy.context.active_object
                    <br />
                    <br />
                    # Point camera at the origin
                    <br />
                    cam.rotation_euler = (0.9, 0, 0.8)
                    <br />
                    <br />
                    # Set this as the active camera
                    <br />
                    bpy.context.scene.camera = cam
                  </div>
                </div>
              )}
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center p-4">
            {isRefreshingViewport ? (
              <>
                <RefreshCcw className="h-10 w-10 animate-spin text-primary/40 mb-3" />
                <p className="text-primary/60">Capturing viewport...</p>
              </>
            ) : (
              <>
                {activeImageSource === "render" ? (
                  <Image className="h-10 w-10 text-primary/30 mb-3" />
                ) : (
                  <Camera className="h-10 w-10 text-primary/30 mb-3" />
                )}
                <p className="text-primary/60 mb-2">
                  No {activeImageSource === "render" ? "render" : "viewport"}{" "}
                  image available
                </p>
                {activeImageSource === "viewport" && (
                  <button
                    className="px-4 py-2 bg-primary text-secondary rounded-md"
                    onClick={refreshViewport}
                  >
                    Capture Viewport
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ViewportPanel;
