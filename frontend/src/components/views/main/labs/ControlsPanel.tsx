import React from "react";
import {
  PlayCircle,
  RefreshCcw,
  Plus,
  Box,
  Layers,
  Image,
  List,
  Code,
  ChevronDown,
  ChevronUp,
  Command,
  MessageSquare,
  Database,
} from "lucide-react";
import { Tabs, Button } from "antd";
import { ConnectionStatus, Job } from "../../../utils/blenderapi";
import ProjectManagerPanel from "./ProjectManagerPanel";
import ChatPanel from "./ChatPanel";

interface CodeExamples {
  [key: string]: string;
}

interface ControlsPanelProps {
  connectionStatus: ConnectionStatus;
  isExecutingCommand: boolean;
  isJobHistoryOpen: boolean;
  isLoadingJobHistory: boolean;
  jobHistory: Job[];
  input: string;
  output: string;
  codeExamples: CodeExamples;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  setOutput: React.Dispatch<React.SetStateAction<string>>;
  setIsJobHistoryOpen: React.Dispatch<React.SetStateAction<boolean>>;
  fetchJobHistory: () => void;
  executeCode: () => void;
  handleAddRandomSphere: () => void;
  handleAddRandomCube: () => void;
  handleRenderScene: () => void;
  handleGetSceneInfo: () => void;
  handleClearScene: () => void;
  handleAddCamera: () => void;
  showFeedback: (message: string, type: "success" | "error" | "info") => void;
  executeBlenderCommand: (
    commandFn: () => Promise<{ job_id: string }>,
    actionName: string,
    skipViewportRefresh?: boolean
  ) => void;
  refreshViewport?: () => Promise<void>;
}

const ControlsPanel: React.FC<ControlsPanelProps> = ({
  connectionStatus,
  isExecutingCommand,
  isJobHistoryOpen,
  isLoadingJobHistory,
  jobHistory,
  input,
  output,
  codeExamples,
  setInput,
  setOutput,
  setIsJobHistoryOpen,
  fetchJobHistory,
  executeCode,
  handleAddRandomSphere,
  handleAddRandomCube,
  handleRenderScene,
  handleGetSceneInfo,
  handleClearScene,
  handleAddCamera,
  showFeedback,
  executeBlenderCommand,
  refreshViewport = async () => {}, // Default to empty function if not provided
}) => {
  const setCodeExample = (exampleKey: string) => {
    setInput(codeExamples[exampleKey]);
  };

  return (
    <div className="flex flex-col gap-4">
      <h3 className="font-medium text-lg flex items-center gap-2">
        <Command className="h-5 w-5 text-accent" />
        Blender Controls
      </h3>
      <Tabs defaultActiveKey="1">
        <Tabs.TabPane
          tab={
            <span className="flex items-center gap-1">
              <MessageSquare className="h-4 w-4" /> Chat
            </span>
          }
          key="1"
        >
          <ChatPanel
            connectionStatus={connectionStatus}
            refreshViewport={refreshViewport}
          />
        </Tabs.TabPane>
        <Tabs.TabPane
          tab={
            <span className="flex items-center gap-1">
              <PlayCircle className="h-4 w-4" /> Presets
            </span>
          }
          key="2"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Clear Scene - now first */}
            <div className="border rounded-lg p-3 hover:bg-primary/5 transition">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">Clear Scene</h3>
                <RefreshCcw className="h-5 w-5 text-accent" />
              </div>
              <p className="text-sm text-primary/60 mb-3">
                Delete all objects from the scene
              </p>
              <Button
                type="primary"
                className="w-full flex items-center justify-center gap-1 px-3 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleClearScene}
                disabled={
                  isExecutingCommand || connectionStatus.status !== "success"
                }
              >
                {isExecutingCommand ? (
                  <RefreshCcw className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCcw className="h-4 w-4" />
                )}
                Clear Scene
              </Button>
            </div>

            {/* Add Random Sphere */}
            <div className="border rounded-lg p-3 hover:bg-primary/5 transition">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">Add Sphere</h3>
                <Box className="h-5 w-5 text-accent" />
              </div>
              <p className="text-sm text-primary/60 mb-3">
                Add a sphere with random position
              </p>
              <Button
                type="primary"
                className="w-full flex items-center justify-center gap-1 px-3 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleAddRandomSphere}
                disabled={
                  isExecutingCommand || connectionStatus.status !== "success"
                }
              >
                {isExecutingCommand ? (
                  <RefreshCcw className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Add Sphere
              </Button>
            </div>

            {/* Add Random Cube */}
            <div className="border rounded-lg p-3 hover:bg-primary/5 transition">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">Add Cube</h3>
                <Box className="h-5 w-5 text-accent" />
              </div>
              <p className="text-sm text-primary/60 mb-3">
                Add a cube with random position
              </p>
              <Button
                type="primary"
                className="w-full flex items-center justify-center gap-1 px-3 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleAddRandomCube}
                disabled={
                  isExecutingCommand || connectionStatus.status !== "success"
                }
              >
                {isExecutingCommand ? (
                  <RefreshCcw className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Add Cube
              </Button>
            </div>

            {/* Render Scene */}
            <div className="border rounded-lg p-3 hover:bg-primary/5 transition">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">Render Scene</h3>
                <Image className="h-5 w-5 text-accent" />
              </div>
              <p className="text-sm text-primary/60 mb-3">
                Create a full render of the scene
              </p>
              <Button
                type="primary"
                className="w-full flex items-center justify-center gap-1 px-3 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleRenderScene}
                disabled={
                  isExecutingCommand || connectionStatus.status !== "success"
                }
              >
                {isExecutingCommand ? (
                  <RefreshCcw className="h-4 w-4 animate-spin" />
                ) : (
                  <PlayCircle className="h-4 w-4" />
                )}
                Render
              </Button>
            </div>

            {/* Add Camera */}
            <div className="border rounded-lg p-3 hover:bg-primary/5 transition">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">Add Camera</h3>
                <Image className="h-5 w-5 text-accent" />
              </div>
              <p className="text-sm text-primary/60 mb-3">
                Add a new camera to the scene
              </p>
              <Button
                type="primary"
                className="w-full flex items-center justify-center gap-1 px-3 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleAddCamera}
                disabled={
                  isExecutingCommand || connectionStatus.status !== "success"
                }
              >
                {isExecutingCommand ? (
                  <RefreshCcw className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Add Camera
              </Button>
            </div>
            {/* Scene Info button removed/hidden */}
          </div>
        </Tabs.TabPane>
        {/* <Tabs.TabPane
          tab={
            <span className="flex items-center gap-1">
              <Code className="h-4 w-4" /> Code
            </span>
          }
          key="3"
        >
          <div className="p-3 border rounded-lg">
            <div className="mb-3">
              <label className="text-sm font-medium block mb-2">
                Example Code Templates:
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  className="px-2 py-1 bg-accent/10 hover:bg-accent/20 text-accent rounded-md text-sm"
                  onClick={() => setCodeExample("addCube")}
                >
                  Add Red Cube
                </button>
                <button
                  className="px-2 py-1 bg-accent/10 hover:bg-accent/20 text-accent rounded-md text-sm"
                  onClick={() => setCodeExample("arrangeObjects")}
                >
                  Arrange Objects
                </button>
                <button
                  className="px-2 py-1 bg-accent/10 hover:bg-accent/20 text-accent rounded-md text-sm"
                  onClick={() => setCodeExample("animateCube")}
                >
                  Animate Cube
                </button>
              </div>
            </div>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Enter Python code to execute in Blender..."
              className="w-full mb-3 p-3 border rounded-md font-mono text-sm resize-none focus:outline-none focus:ring-1 focus:ring-accent h-56 bg-white dark:bg-gray-800 text-primary dark:text-gray-200 dark:border-gray-700"
              rows={6}
            />
            <div className="flex gap-2">
              <button
                className="flex items-center gap-1 px-3 py-2 bg-primary hover:bg-primary/80 text-secondary rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={executeCode}
                disabled={
                  isExecutingCommand || connectionStatus.status !== "success"
                }
              >
                {isExecutingCommand ? (
                  <RefreshCcw className="h-4 w-4 animate-spin" />
                ) : (
                  <PlayCircle className="h-4 w-4" />
                )}
                Run Code
              </button>
              <button
                className="flex items-center gap-1 px-3 py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-md"
                onClick={() => setInput("")}
              >
                Clear
              </button>
            </div>
            {output && (
              <div className="mt-3">
                <div className="flex justify-between items-center mb-1">
                  <h4 className="text-sm font-medium">Output:</h4>
                  <button
                    className="text-xs text-primary/50 hover:text-primary/70"
                    onClick={() => setOutput("")}
                  >
                    Clear
                  </button>
                </div>
                <div className="bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-green-400 p-3 rounded font-mono text-xs overflow-auto max-h-40 border dark:border-gray-700">
                  <pre>{output}</pre>
                </div>
              </div>
            )}
          </div>
        </Tabs.TabPane> */}
        <Tabs.TabPane
          tab={
            <span className="flex items-center gap-1">
              <Database className="h-4 w-4" /> Projects
            </span>
          }
          key="4"
        >
          <ProjectManagerPanel
            connectionStatus={connectionStatus}
            isExecutingCommand={isExecutingCommand}
            showFeedback={showFeedback}
            executeBlenderCommand={executeBlenderCommand}
            refreshViewport={async () => {}}
          />
        </Tabs.TabPane>
      </Tabs>
      <div className="border rounded-lg overflow-hidden mt-2">
        <button
          className="w-full p-3 flex justify-between items-center bg-primary/5 hover:bg-primary/10 transition"
          onClick={() => {
            setIsJobHistoryOpen(!isJobHistoryOpen);
            if (!isJobHistoryOpen) fetchJobHistory();
          }}
        >
          <div className="flex items-center gap-2">
            <List className="h-5 w-5 text-accent" />
            <span className="font-medium">Job History</span>
          </div>
          {isJobHistoryOpen ? (
            <ChevronUp className="h-5 w-5 text-primary/60" />
          ) : (
            <ChevronDown className="h-5 w-5 text-primary/60" />
          )}
        </button>
        {isJobHistoryOpen && (
          <div className="p-3">
            {isLoadingJobHistory ? (
              <div className="text-center py-4">
                <RefreshCcw className="h-8 w-8 animate-spin text-primary/40 mx-auto" />
                <p className="text-sm text-primary/60 mt-2">
                  Loading job history...
                </p>
              </div>
            ) : jobHistory.length === 0 ? (
              <div className="text-center py-4">
                <p className="text-sm text-primary/60">No jobs available yet</p>
              </div>
            ) : (
              <div className="max-h-60 overflow-y-auto">
                <ul className="divide-y">
                  {jobHistory.slice(0, 10).map((job) => (
                    <li key={job.id} className="py-2">
                      <div className="flex justify-between">
                        <div className="text-sm font-medium">
                          {job.command_type}
                        </div>
                        <div
                          className={`text-xs font-medium ${
                            job.status === "completed"
                              ? "text-green-500"
                              : job.status === "failed"
                              ? "text-red-500"
                              : job.status === "processing"
                              ? "text-yellow-500"
                              : "text-gray-500"
                          }`}
                        >
                          {job.status.toUpperCase()}
                        </div>
                      </div>
                      <div className="text-xs text-primary/50 mt-1">
                        Created:{" "}
                        {new Date(job.created_at * 1000).toLocaleString()}
                      </div>
                    </li>
                  ))}
                </ul>
                {jobHistory.length > 10 && (
                  <div className="text-center mt-2">
                    <span className="text-sm text-primary/60">
                      Showing 10 of {jobHistory.length} jobs
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ControlsPanel;
