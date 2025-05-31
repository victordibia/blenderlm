import React, { useState, useEffect, useRef } from "react";
import { CheckCircle, AlertCircle, RefreshCcw } from "lucide-react";
import BlenderAPI, { ConnectionStatus, Job } from "../../../utils/blenderapi";

// Import our components
import ConnectionStatusComponent from "./ConnectionStatus";
import ViewportPanel from "./ViewportPanel";
import ControlsPanel from "./ControlsPanel";

// Define ActionFeedback and CodeExamples types locally
interface ActionFeedback {
  message: string;
  type: "success" | "error" | "info";
  visible: boolean;
}

interface CodeExamples {
  [key: string]: string;
}

const ManualControlLab: React.FC = () => {
  // State variables
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    status: "fetching", // Initial state
  });
  const [isCheckingConnection, setIsCheckingConnection] = useState(true); // Start with true as we fetch on mount
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [renderedImage, setRenderedImage] = useState<string | null>(null);
  const [activeImageSource, setActiveImageSource] = useState<
    "viewport" | "render"
  >("viewport");
  const [isViewportMinimized, setIsViewportMinimized] = useState(false);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [isRefreshingViewport, setIsRefreshingViewport] = useState(false);
  const [isExecutingCommand, setIsExecutingCommand] = useState(false);
  const [jobHistory, setJobHistory] = useState<Job[]>([]);
  const [isJobHistoryOpen, setIsJobHistoryOpen] = useState(false);
  const [isLoadingJobHistory, setIsLoadingJobHistory] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<ActionFeedback>({
    message: "",
    type: "info",
    visible: false,
  });
  const [errorMessage, setErrorMessage] = useState<string | undefined>(
    undefined
  );

  // Chat related state
  const [chatInput, setChatInput] = useState<string>("");
  const [chatMessages, setChatMessages] = useState<
    Array<{ role: string; content: string; id?: string }>
  >([
    {
      role: "system",
      content:
        "Hello! I'm your Blender assistant. Try asking me to create objects like 'Add a red cube' or 'Create a blue sphere at position [1, 2, 0]'.",
    },
  ]);
  const [isProcessingChat, setIsProcessingChat] = useState<boolean>(false);

  // Default Python code examples
  const codeExamples: CodeExamples = {
    addCube: `# Add a simple red cube at the origin
import bpy

# Create a cube
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
cube = bpy.context.active_object
cube.name = "RedCube"

# Create a red material
mat = bpy.data.materials.new(name="Red_Material")
mat.use_nodes = True
principled = mat.node_tree.nodes.get('Principled BSDF')
if principled:
    principled.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)

# Assign material to cube
if cube.data.materials:
    cube.data.materials[0] = mat
else:
    cube.data.materials.append(mat)`,

    arrangeObjects: `# Create and arrange multiple objects
import bpy
import random
import math

# Clear existing objects
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)

# Create a collection of different objects in a circle
radius = 5
num_objects = 8

for i in range(num_objects):
    # Calculate position on the circle
    angle = (2.0 * math.pi * i) / num_objects
    x = radius * math.cos(angle)
    y = radius * math.sin(angle)
    
    # Alternate between different primitive types
    if i % 4 == 0:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 0))
    elif i % 4 == 1:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, location=(x, y, 0))
    elif i % 4 == 2:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.7, depth=1.5, location=(x, y, 0))
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=0.8, location=(x, y, 0))
    
    # Create a random colored material
    obj = bpy.context.active_object
    mat = bpy.data.materials.new(name=f"Material_{i}")
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get('Principled BSDF')
    if principled:
        r, g, b = random.random(), random.random(), random.random()
        principled.inputs['Base Color'].default_value = (r, g, b, 1.0)
    
    # Assign the material
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
        
# Add a central sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5, location=(0, 0, 0))
central = bpy.context.active_object
central.name = "CentralSphere"

# Create a white material
mat = bpy.data.materials.new(name="White_Material")
mat.use_nodes = True
principled = mat.node_tree.nodes.get('Principled BSDF')
if principled:
    principled.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)

# Assign material to central sphere
if central.data.materials:
    central.data.materials[0] = mat
else:
    central.data.materials.append(mat)`,

    animateCube: `# Create a simple animation
import bpy
import math

# Clear existing objects
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)

# Create a cube
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
cube = bpy.context.active_object
cube.name = "AnimatedCube"

# Create a blue material
mat = bpy.data.materials.new(name="Blue_Material")
mat.use_nodes = True
principled = mat.node_tree.nodes.get('Principled BSDF')
if principled:
    principled.inputs['Base Color'].default_value = (0.0, 0.3, 1.0, 1.0)

# Assign material to cube
if cube.data.materials:
    cube.data.materials[0] = mat
else:
    cube.data.materials.append(mat)

# Set up animation (this won't play automatically but will set the keyframes)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 100

# Location animation
cube.location = (0, 0, 0)
cube.keyframe_insert(data_path="location", frame=1)

cube.location = (3, 0, 0)
cube.keyframe_insert(data_path="location", frame=25)

cube.location = (3, 3, 0)
cube.keyframe_insert(data_path="location", frame=50)

cube.location = (0, 3, 0)
cube.keyframe_insert(data_path="location", frame=75)

cube.location = (0, 0, 0)
cube.keyframe_insert(data_path="location", frame=100)

# Rotation animation
cube.rotation_euler = (0, 0, 0)
cube.keyframe_insert(data_path="rotation_euler", frame=1)

cube.rotation_euler = (0, 0, math.radians(180))
cube.keyframe_insert(data_path="rotation_euler", frame=50)

cube.rotation_euler = (0, 0, math.radians(360))
cube.keyframe_insert(data_path="rotation_euler", frame=100)

print("Animation keyframes created - use the timeline to view the animation")`,
  };

  // References
  const viewportRef = useRef<HTMLDivElement>(null);

  // Initial data loading
  useEffect(() => {
    const initializeWorkspace = async () => {
      // checkConnection will set the status to fetching, then success/failed
      await checkConnection();
      // No need to check connectionStatus.connected here, checkConnection handles it
      // and subsequent actions should rely on the new status values.
      // If the initial checkConnection leads to "success", then refresh.
      // This logic might need adjustment based on how checkConnection updates status.
    };

    initializeWorkspace();
  }, []);

  // Check connection with Blender
  const checkConnection = async () => {
    setIsCheckingConnection(true);
    setConnectionStatus({ status: "fetching" }); // Set to fetching at the start
    try {
      const status = await BlenderAPI.checkConnection();
      setConnectionStatus(status); // status from API will be {status: "success"} or {status: "failed", error: "..."}
      // If connection successful, auto-refresh viewport
      if (status.status === "success") {
        refreshViewport();
        fetchJobHistory(); // Fetch history on successful initial connection
      }
    } catch (error) {
      // The API.checkConnection should ideally return the {status: "failed", error: "..."} object
      // But if it throws an error before that, we catch it here.
      setConnectionStatus({
        status: "failed",
        error: `Cannot connect to BlenderLM API: ${error}`,
      });
    } finally {
      setIsCheckingConnection(false);
    }
  };

  // Fetch job history
  const fetchJobHistory = async () => {
    setIsLoadingJobHistory(true);
    try {
      const jobs = await BlenderAPI.fetchJobs();
      setJobHistory(jobs);
    } catch (error) {
      showFeedback(`Error fetching job history: ${error}`, "error");
    } finally {
      setIsLoadingJobHistory(false);
    }
  };

  // Refresh viewport
  const refreshViewport = async () => {
    setIsRefreshingViewport(true);
    try {
      showFeedback("Capturing viewport...", "info");
      const result = await BlenderAPI.captureViewport();

      // Fetch job details to get the image
      await pollJobUntilComplete(result.job_id);
      showFeedback("Viewport refreshed", "success");
    } catch (error) {
      showFeedback(`Failed to refresh viewport: ${error}`, "error");
    } finally {
      setIsRefreshingViewport(false);
    }
  };

  // Execute a Blender command
  const executeBlenderCommand = async (
    commandFn: () => Promise<{ job_id: string }>,
    actionName: string,
    skipViewportRefresh: boolean = false
  ) => {
    if (connectionStatus.status !== "success") {
      showFeedback("Not connected to Blender", "error");
      return;
    }

    setIsExecutingCommand(true);
    showFeedback(`Executing ${actionName}...`, "info");

    try {
      const result = await commandFn();

      // Poll for job completion
      await pollJobUntilComplete(result.job_id);

      // Refresh viewport to show changes (unless skipped - e.g. for render)
      if (!skipViewportRefresh) {
        refreshViewport();
      }

      // Update job history
      fetchJobHistory();

      showFeedback(`${actionName} completed successfully`, "success");
    } catch (error) {
      showFeedback(`Error executing ${actionName}: ${error}`, "error");
    } finally {
      setIsExecutingCommand(false);
    }
  };

  // Poll a job until it completes
  const pollJobUntilComplete = async (jobId: string) => {
    let jobComplete = false;
    let pollCount = 0;
    const maxPolls = 20; // To prevent infinite polling

    // Clear any previous error message when starting a new job
    setErrorMessage(undefined);

    while (!jobComplete && pollCount < maxPolls) {
      try {
        const job = await BlenderAPI.fetchJobDetails(jobId);

        if (!job) {
          throw new Error("Job not found");
        }

        setActiveJob(job);

        if (job.status === "completed") {
          jobComplete = true;

          // Check if the job result has an error status (some APIs use this approach)
          if (job.result?.status === "error") {
            jobComplete = true;
            const errorMsg = job.result.message || "Unknown error";
            console.error("Job returned error:", errorMsg);
            setErrorMessage(errorMsg);
            throw new Error(errorMsg);
          }

          // Handle different image-producing jobs appropriately
          if (job.command_type === "render_scene") {
            // For rendered images
            console.log("Render scene job completed successfully!");
            console.log("Job result:", job.result);

            if (job.result?.image_data) {
              console.log(
                "Render image data (start of string):",
                job.result.image_data.substring(0, 100) + "..."
              );
              setRenderedImage(job.result.image_data);
              setPreviewImage(job.result.image_data);
              setActiveImageSource("render");
              setErrorMessage(undefined);
            } else if (job.result?.image_base64) {
              console.log(
                "Render image base64 (start of string):",
                job.result.image_base64.substring(0, 100) + "..."
              );
              const imageUrl = `data:image/jpeg;base64,${job.result.image_base64}`;
              setRenderedImage(imageUrl);
              setPreviewImage(imageUrl);
              setActiveImageSource("render");
              setErrorMessage(undefined);
            } else {
              console.warn(
                "Render scene job completed but no image data was found in the result:",
                job.result
              );
              // Show a user-friendly warning when no image is returned
              if (job.result?.status === "error") {
                const errorMsg =
                  job.result?.message || "Render failed - no image produced";
                setErrorMessage(errorMsg);
                throw new Error(errorMsg);
              } else {
                setErrorMessage("Render failed - no image produced");
                throw new Error("Render failed - no image produced");
              }
            }
          } else if (job.command_type === "capture_viewport") {
            // For viewport captures
            if (job.result?.image_data) {
              setPreviewImage(job.result.image_data);
              setActiveImageSource("viewport");
              setErrorMessage(undefined);
            } else if (job.result?.image_base64) {
              const imageUrl = `data:image/jpeg;base64,${job.result.image_base64}`;
              setPreviewImage(imageUrl);
              setActiveImageSource("viewport");
              setErrorMessage(undefined);
            } else if (job.result?.status === "error") {
              const errorMsg =
                job.result?.message || "Failed to capture viewport";
              setErrorMessage(errorMsg);
              throw new Error(errorMsg);
            }
          }

          // Set output for Python code execution
          if (job.command_type === "execute_code") {
            setOutput(JSON.stringify(job.result, null, 2));
          }
        } else if (job.status === "failed") {
          jobComplete = true;
          console.error("Job failed:", job.error);
          setErrorMessage(job.error || "Job failed with unknown error");
          throw new Error(job.error || "Job failed");
        }

        if (!jobComplete) {
          // Wait before polling again
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
      } catch (error) {
        console.error("Error polling job:", error);
        // Set the error message if it hasn't been set already
        if (!errorMessage) {
          setErrorMessage(
            error instanceof Error ? error.message : String(error)
          );
        }
        throw error;
      }

      pollCount++;
    }

    if (!jobComplete) {
      const timeoutMsg = "Job timed out";
      setErrorMessage(timeoutMsg);
      throw new Error(timeoutMsg);
    }
  };

  // Show temporary feedback message
  const showFeedback = (
    message: string,
    type: "success" | "error" | "info"
  ) => {
    setActionFeedback({
      message,
      type,
      visible: true,
    });

    // Hide after 3 seconds
    setTimeout(() => {
      setActionFeedback((prev) => ({ ...prev, visible: false }));
    }, 3000);
  };

  // Download rendered image
  const downloadImage = () => {
    if (!previewImage) return;

    const link = document.createElement("a");
    link.href = previewImage;
    link.download = "blender-render.png";
    link.click();
  };

  // Execute Python code
  const executeCode = () => {
    if (!input.trim()) {
      showFeedback("Please enter some code to execute", "error");
      return;
    }

    executeBlenderCommand(() => BlenderAPI.executeCode(input), "Python code");
  };

  // Handle the various preset actions
  const handleAddRandomSphere = () => {
    executeBlenderCommand(
      () => BlenderAPI.addRandomSphere(),
      "Add Random Sphere"
    );
  };

  const handleAddRandomCube = () => {
    executeBlenderCommand(() => BlenderAPI.addRandomCube(), "Add Random Cube");
  };

  const handleAddRandomMaterial = () => {
    executeBlenderCommand(
      () => BlenderAPI.addRandomMaterial(),
      "Add Random Material"
    );
  };

  const handleRenderScene = () => {
    executeBlenderCommand(() => BlenderAPI.renderScene(), "Render Scene", true);
  };

  const handleGetSceneInfo = () => {
    executeBlenderCommand(() => BlenderAPI.getSceneInfo(), "Get Scene Info");
  };

  const handleClearScene = () => {
    executeBlenderCommand(() => BlenderAPI.clearScene(), "Clear Scene");
  };

  const handleAddCamera = () => {
    executeBlenderCommand(
      () =>
        BlenderAPI.addCamera({
          location: [0, -10, 5],
          rotation: [1.2, 0, 0],
        }),
      "Add Camera"
    );
  };

  // Handle chat submission
  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !chatInput.trim() ||
      isProcessingChat ||
      connectionStatus.status !== "success"
    )
      return;

    // Add user message to chat
    const userMessage = { role: "user", content: chatInput };
    setChatMessages((prev) => [...prev, userMessage]);

    // Clear input and set processing state
    const currentQuery = chatInput;
    setChatInput("");
    setIsProcessingChat(true);

    try {
      // Add a temporary loading message
      const loadingId = Date.now().toString();
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Thinking...", id: loadingId },
      ]);

      // Process the query
      const response = await BlenderAPI.processChat(currentQuery);

      if (response.status === "success" && response.response) {
        // Remove the loading message
        setChatMessages((prev) => prev.filter((msg) => msg.id !== loadingId));

        // Add the single assistant message from response.response.content
        const assistantMessage = {
          role: "assistant",
          content:
            response.response.content || "Assistant processed the request.",
        };

        setChatMessages((prev) => [...prev, assistantMessage]);

        // Refresh viewport to show any changes made
        await refreshViewport();
      } else {
        // Remove the loading message
        setChatMessages((prev) => prev.filter((msg) => msg.id !== loadingId));
        // Add error message
        setChatMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${
              response.error ||
              response.detail ||
              "Failed to process query or invalid response structure"
            }`,
          },
        ]);
      }
    } catch (error) {
      // Add error message
      setChatMessages((prev) => [
        ...prev.filter((msg) => !("id" in msg)),
        { role: "assistant", content: `Error: ${error}` },
      ]);
    } finally {
      setIsProcessingChat(false);
    }
  };

  // Render the action feedback toast
  const renderActionFeedback = () => {
    if (!actionFeedback.visible) return null;

    const bgColorClass =
      actionFeedback.type === "success"
        ? "bg-green-100 text-green-800 border-green-200"
        : actionFeedback.type === "error"
        ? "bg-red-100 text-red-800 border-red-200"
        : "bg-blue-100 text-blue-800 border-blue-200";

    return (
      <div
        className={`fixed top-4 right-4 p-3 rounded-md shadow-md border ${bgColorClass} z-50 max-w-md animate-fade-in`}
      >
        <div className="flex items-center gap-2">
          {actionFeedback.type === "success" && (
            <CheckCircle className="h-4 w-4" />
          )}
          {actionFeedback.type === "error" && (
            <AlertCircle className="h-4 w-4" />
          )}
          {actionFeedback.type === "info" && (
            <RefreshCcw className="h-4 w-4 animate-spin" />
          )}
          <span>{actionFeedback.message}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full gap-4 w-full max-w-full px-0">
      {/* Action Feedback Toast */}
      {renderActionFeedback()}

      {/* Connection Status Component - Always visible */}
      <ConnectionStatusComponent
        connectionStatus={connectionStatus}
        isCheckingConnection={isCheckingConnection} // This prop might become redundant
        checkConnection={checkConnection}
      />

      {/* Main Content: Side by Side Layout - Conditionally rendered */}
      {connectionStatus.status === "success" && (
        <div className="flex flex-col xl:flex-row gap-6 flex-grow">
          {/* Left Panel: Controls and Project Manager */}
          <div className="flex flex-col flex-1 min-w-0 gap-6">
            {/* Project Manager Panel */}

            {/* Controls Panel */}
            <ControlsPanel
              connectionStatus={connectionStatus}
              isExecutingCommand={isExecutingCommand}
              isJobHistoryOpen={isJobHistoryOpen}
              isLoadingJobHistory={isLoadingJobHistory}
              jobHistory={jobHistory}
              input={input}
              output={output}
              chatInput={chatInput}
              chatMessages={chatMessages}
              isProcessingChat={isProcessingChat}
              codeExamples={codeExamples}
              setInput={setInput}
              setOutput={setOutput}
              setChatInput={setChatInput}
              setIsJobHistoryOpen={setIsJobHistoryOpen}
              fetchJobHistory={fetchJobHistory}
              executeCode={executeCode}
              handleChatSubmit={handleChatSubmit}
              handleAddRandomSphere={handleAddRandomSphere}
              handleAddRandomCube={handleAddRandomCube}
              handleAddRandomMaterial={handleAddRandomMaterial}
              handleRenderScene={handleRenderScene}
              handleGetSceneInfo={handleGetSceneInfo}
              handleClearScene={handleClearScene}
              handleAddCamera={handleAddCamera}
              showFeedback={showFeedback}
              executeBlenderCommand={executeBlenderCommand}
            />
          </div>

          {/* Right Panel: Viewport and Scene Info */}
          <div className="flex flex-col flex-shrink-0 max-w-[600px] w-full xl:w-[600px] gap-6 items-center justify-center">
            {/* Viewport */}
            <ViewportPanel
              connectionStatus={connectionStatus}
              previewImage={previewImage}
              renderedImage={renderedImage}
              activeImageSource={activeImageSource}
              isViewportMinimized={isViewportMinimized}
              isRefreshingViewport={isRefreshingViewport}
              refreshViewport={refreshViewport}
              downloadImage={downloadImage}
              setIsViewportMinimized={setIsViewportMinimized}
              errorMessage={errorMessage}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ManualControlLab;
