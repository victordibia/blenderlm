import React, { useState, useEffect, useRef } from "react";
import {
  RefreshCcw,
  Camera,
  AlertCircle,
  Download,
  Maximize,
  X,
  Image,
  ChevronDown,
} from "lucide-react";
import BlenderAPI, { Job } from "../../../utils/blenderapi";
import { ConnectionStatus as ConnectionStatusType } from "../../../utils/blenderapi"; // Import ConnectionStatusType

// --- SceneInfoPanel component ---
interface SceneInfoPanelProps {
  sceneInfo: any;
  sceneLoading: boolean;
  sceneError: string | null;
  sceneExpanded: boolean;
  setSceneExpanded: (v: boolean) => void;
  imageWidth: string | number;
}

const SceneInfoPanel: React.FC<SceneInfoPanelProps> = ({
  sceneInfo,
  sceneLoading,
  sceneError,
  sceneExpanded,
  setSceneExpanded,
  imageWidth,
}) => {
  // Icon for object type (compact)
  const objectTypeIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case "mesh":
      case "cube":
        return "📦";
      case "sphere":
        return "🔵";
      case "cylinder":
        return "🥫";
      case "cone":
        return "🔺";
      case "camera":
        return "📷";
      case "light":
      case "lamp":
        return "💡";
      case "empty":
        return "⭐";
      default:
        return "🧩";
    }
  };

  return (
    <div
      className="mt-10 rounded-lg border border-accent shadow-sm text-sm bg-primary text-primary flex justify-center"
      style={{
        width: imageWidth,
        minWidth: 200,
        maxWidth: "100%",
        margin: "0 auto",
      }}
    >
      <button
        className="w-full flex items-center justify-between px-3 py-2 focus:outline-none hover:bg-secondary transition rounded-lg"
        onClick={() => setSceneExpanded(!sceneExpanded)}
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-primary">
            {sceneInfo?.name || "Scene"}
          </span>
          <span className="ml-2 text-xs text-secondary">
            {sceneInfo?.object_count ?? "-"} objects
          </span>
        </div>
        <span
          className={`transition-transform ${
            sceneExpanded ? "rotate-180" : "rotate-0"
          }`}
        >
          <ChevronDown className="h-4 w-4 text-secondary" />
        </span>
      </button>
      {sceneExpanded && (
        <div className="px-3 pb-2 pt-1">
          {sceneLoading ? (
            <div className="flex items-center gap-2 text-secondary py-2">
              <RefreshCcw className="h-4 w-4 animate-spin text-accent" />
              Loading scene info...
            </div>
          ) : sceneError ? (
            <div className="text-xs text-accent py-2">{sceneError}</div>
          ) : sceneInfo ? (
            <>
              <div className="flex gap-4 mb-2">
                <div>
                  <span className="text-secondary">Materials:</span>{" "}
                  {sceneInfo.materials_count || 0}
                </div>
                <div>
                  <span className="text-secondary">Last Updated:</span>{" "}
                  {new Date().toLocaleTimeString()}
                </div>
              </div>
              {sceneInfo.objects && sceneInfo.objects.length > 0 ? (
                <div className="overflow-auto max-h-32 border rounded border-accent">
                  <table className="min-w-full divide-y divide-accent text-xs bg-primary text-primary">
                    <thead className="bg-secondary">
                      <tr>
                        <th className="px-2 py-1 text-left font-medium text-secondary uppercase tracking-wider">
                          Type
                        </th>
                        <th className="px-2 py-1 text-left font-medium text-secondary uppercase tracking-wider">
                          Name
                        </th>
                        <th className="px-2 py-1 text-left font-medium text-secondary uppercase tracking-wider">
                          Location
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {sceneInfo.objects.map((obj: any, idx: number) => (
                        <tr key={idx} className="hover:bg-secondary/40">
                          <td className="px-2 py-1 whitespace-nowrap">
                            <span className="mr-1">
                              {objectTypeIcon(obj.type)}
                            </span>
                            <span className="text-secondary">{obj.type}</span>
                          </td>
                          <td className="px-2 py-1 whitespace-nowrap text-primary">
                            {obj.name}
                          </td>
                          <td className="px-2 py-1 whitespace-nowrap text-secondary">
                            [
                            {obj.location
                              ?.map((val: number) => val.toFixed(2))
                              .join(", ")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-2 text-center text-secondary text-xs">
                  No objects in this scene
                </div>
              )}
            </>
          ) : (
            <div className="p-2 text-center text-secondary text-xs">
              No scene information available
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface ViewportPanelProps {
  connectionStatus: ConnectionStatusType; // Use the imported tri-state type
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
  // Scene Info State (compact, embedded)
  const [sceneLoading, setSceneLoading] = useState<boolean>(false);
  const [sceneError, setSceneError] = useState<string | null>(null);
  const [sceneInfo, setSceneInfo] = useState<any>(null);
  const [sceneJobInfo, setSceneJobInfo] = useState<Job | null>(null);
  const [sceneExpanded, setSceneExpanded] = useState<boolean>(false);
  const [isImageModalOpen, setIsImageModalOpen] = useState(false);

  // Ref and state for image width
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [imageWidth, setImageWidth] = useState<string | number>("100%");

  // Fetch scene info logic (compact, polling)
  const fetchSceneInfo = async () => {
    setSceneLoading(true);
    setSceneError(null);
    try {
      const response = await BlenderAPI.getSceneInfo();
      const jobId = response.job_id;
      if (!jobId) throw new Error("No job ID returned from server");
      const pollInterval = setInterval(async () => {
        try {
          const jobDetails = await BlenderAPI.fetchJobDetails(jobId);
          setSceneJobInfo(jobDetails);
          if (!jobDetails) {
            clearInterval(pollInterval);
            setSceneError("Failed to fetch job details");
            setSceneLoading(false);
            return;
          }
          if (jobDetails.status === "completed" && jobDetails.result) {
            clearInterval(pollInterval);
            setSceneInfo(jobDetails.result);
            setSceneLoading(false);
          } else if (jobDetails.status === "failed") {
            clearInterval(pollInterval);
            setSceneError(jobDetails.error || "Job failed");
            setSceneLoading(false);
          }
        } catch (err) {
          clearInterval(pollInterval);
          setSceneError(`Error polling job: ${err}`);
          setSceneLoading(false);
        }
      }, 1000);
      return () => clearInterval(pollInterval);
    } catch (err) {
      setSceneError(`Error fetching scene info: ${err}`);
      setSceneLoading(false);
    }
  };

  useEffect(() => {
    fetchSceneInfo();
    // eslint-disable-next-line
  }, []);

  // Update image width when image loads or previewImage changes
  useEffect(() => {
    if (imageRef.current) {
      const updateWidth = () => {
        if (imageRef.current) {
          setImageWidth(imageRef.current.clientWidth);
        }
      };
      updateWidth();
      window.addEventListener("resize", updateWidth);
      return () => window.removeEventListener("resize", updateWidth);
    } else {
      setImageWidth("100%");
    }
  }, [previewImage]);

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
              disabled={
                isRefreshingViewport || connectionStatus.status !== "success"
              }
            >
              {isRefreshingViewport ? (
                <RefreshCcw className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCcw className="h-4 w-4" />
              )}
              Refresh
            </button>
          )}

          {/* Download button */}
          <button
            className="flex items-center gap-1 px-3 py-1 bg-accent/10 hover:bg-accent/20 text-accent rounded-md"
            onClick={downloadImage}
            disabled={!previewImage}
          >
            <Download className="h-4 w-4" />
            Download
          </button>

          {/* Maximize button for full screen image modal */}
          <button
            className="flex items-center justify-center h-8 w-8 bg-primary/5 hover:bg-primary/10 text-primary/70 rounded-md"
            onClick={() => setIsImageModalOpen(true)}
            disabled={!previewImage}
            title="View Fullscreen"
          >
            <Maximize className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="w-full max-w-4xl mx-auto flex flex-col items-center">
        <div
          className={`flex-grow overflow-hidden bg-primary/5 ${
            isViewportMinimized ? "h-16" : "min-h-[300px]"
          } transition-all duration-300 w-full rounded-lg flex items-center justify-center`}
        >
          {isViewportMinimized ? (
            <div className="h-full flex items-center justify-center text-primary/50">
              <span className="text-sm">
                {activeImageSource === "render" ? "Render" : "Viewport"}{" "}
                minimized
              </span>
            </div>
          ) : connectionStatus.status === "fetching" ? (
            <div className="h-full flex flex-col items-center justify-center p-4">
              <RefreshCcw className="h-10 w-10 text-accent animate-spin mb-3" />
              <p className="text-secondary text-center mb-1">
                Connecting to Blender...
              </p>
            </div>
          ) : connectionStatus.status === "failed" ? (
            <div className="h-full flex flex-col items-center justify-center p-4">
              <AlertCircle className="h-10 w-10 text-accent mb-2" />
              <p className="text-secondary text-center mb-1">
                Not connected to Blender
              </p>
              <p className="text-secondary text-sm text-center max-w-md">
                Please ensure Blender is running and the BlenderLM add-on is
                installed, then check the connection status.
              </p>
              {connectionStatus.error && (
                <p className="text-xs text-accent mt-2">
                  (Error: {connectionStatus.error})
                </p>
              )}
            </div>
          ) : previewImage ? (
            <div className="relative h-full flex items-start justify-center w-full">
              <img
                ref={imageRef}
                src={previewImage}
                alt={
                  activeImageSource === "render"
                    ? "Blender Render"
                    : "Blender Viewport"
                }
                className="max-w-full max-h-full object-contain rounded bg-primary cursor-zoom-in"
                style={{ width: "auto", height: "auto" }}
                onLoad={() => {
                  if (imageRef.current)
                    setImageWidth(imageRef.current.clientWidth);
                }}
                onClick={() => setIsImageModalOpen(true)}
              />
              {/* Modal for fullscreen image */}
              {isImageModalOpen && (
                <div
                  className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
                  onClick={() => setIsImageModalOpen(false)}
                >
                  <div
                    className="relative max-w-full max-h-full flex items-center justify-center"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <img
                      src={previewImage}
                      alt="Fullscreen Preview"
                      className="object-contain max-w-[70vw] max-h-[70vh] rounded shadow-lg"
                    />
                    <button
                      className="absolute top-2 right-2 bg-secondary p-2 rounded-full shadow-md hover:bg-primary/10"
                      onClick={() => setIsImageModalOpen(false)}
                      aria-label="Close"
                    >
                      <X className="h-5 w-5 text-secondary" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : errorMessage ? (
            <div className="h-full flex flex-col items-center justify-center p-4">
              <AlertCircle className="h-10 w-10 text-accent mb-3" />
              <p className="text-accent font-medium text-center mb-1">
                Error: {errorMessage}
              </p>
              {activeImageSource === "render" &&
                errorMessage.includes("no camera") && (
                  <div className="mt-3 max-w-md">
                    <p className="text-secondary text-sm text-center mb-3">
                      To fix this error, you need to add a camera to your scene.
                    </p>
                    <div className="bg-secondary text-primary p-3 rounded-md text-xs font-mono border border-accent">
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
                  <RefreshCcw className="h-10 w-10 animate-spin text-accent mb-3" />
                  <p className="text-secondary">Capturing viewport...</p>
                </>
              ) : (
                <>
                  {activeImageSource === "render" ? (
                    <Image className="h-10 w-10 text-accent mb-3" />
                  ) : (
                    <Camera className="h-10 w-10 text-accent mb-3" />
                  )}
                  <p className="text-secondary mb-2">
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
        {/* Compact Scene Info Panel, below viewport, aligned to image width */}
        <div className="mt-4">
          <SceneInfoPanel
            sceneInfo={sceneInfo}
            sceneLoading={sceneLoading}
            sceneError={sceneError}
            sceneExpanded={sceneExpanded}
            setSceneExpanded={setSceneExpanded}
            imageWidth={imageWidth}
          />
        </div>
      </div>
    </div>
  );
};

export default ViewportPanel;
