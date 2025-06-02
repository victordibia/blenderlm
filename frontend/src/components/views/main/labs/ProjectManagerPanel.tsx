import React, { useState, useEffect } from "react";
import {
  FolderOpen,
  Save,
  Trash2,
  Upload,
  RefreshCw,
  Clock,
  Database,
} from "lucide-react";
import { Tabs } from "antd";
import BlenderAPI, {
  ConnectionStatus,
  ProjectInfo,
} from "../../../utils/blenderapi";

interface ProjectManagerPanelProps {
  connectionStatus: ConnectionStatus;
  isExecutingCommand: boolean;
  showFeedback: (message: string, type: "success" | "error" | "info") => void;
  executeBlenderCommand: (
    commandFn: () => Promise<{ job_id: string }>,
    actionName: string,
    skipViewportRefresh?: boolean
  ) => void;
  refreshViewport: () => Promise<void>; // <-- Add this prop
}

const ProjectManagerPanel: React.FC<ProjectManagerPanelProps> = ({
  connectionStatus,
  isExecutingCommand,
  showFeedback,
  executeBlenderCommand,
  refreshViewport, // <-- Destructure here
}) => {
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDescription, setNewProjectDescription] = useState("");

  useEffect(() => {
    if (connectionStatus.status === "success") {
      loadProjects();
    }
  }, [connectionStatus.status]);

  const loadProjects = async () => {
    setIsLoadingProjects(true);
    try {
      const response = await BlenderAPI.listProjects("active", 20);
      setProjects(response.projects);
    } catch (error) {
      showFeedback(`Error loading projects: ${error}`, "error");
    } finally {
      setIsLoadingProjects(false);
    }
  };

  const handleLoadProject = async () => {
    if (!selectedProjectId) {
      showFeedback("Please select a project to load", "error");
      return;
    }
    try {
      const request = { project_id: selectedProjectId };
      const result = await BlenderAPI.loadProject(request);
      executeBlenderCommand(
        () => Promise.resolve({ job_id: result.job_id }),
        "Load Project"
      );
      setSelectedProjectId("");
    } catch (error) {
      showFeedback(`Error loading project: ${error}`, "error");
    }
  };

  const handleSaveProject = async (projectId: string) => {
    try {
      const result = await BlenderAPI.saveProject({
        project_id: projectId,
        create_backup: true,
      });
      executeBlenderCommand(
        () => Promise.resolve({ job_id: result.job_id }),
        "Save Project"
      );
    } catch (error) {
      showFeedback(`Error saving project: ${error}`, "error");
    }
  };

  const handleDeleteProject = async (
    projectId: string,
    projectName: string
  ) => {
    try {
      await BlenderAPI.deleteProject(projectId);
      setProjects(projects.filter((p) => p.id !== projectId));
      showFeedback(`Project "${projectName}" deleted successfully`, "success");
    } catch (error) {
      showFeedback(`Error deleting project: ${error}`, "error");
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      showFeedback("Project name is required", "error");
      return;
    }
    try {
      const request = {
        name: newProjectName.trim(),
        description: newProjectDescription.trim(),
      };
      // Get both project and job_id from backend
      const { project: newProject, job_id } = await BlenderAPI.createProject(
        request
      );
      setProjects([newProject, ...projects]);
      setNewProjectName("");
      setNewProjectDescription("");
      showFeedback(
        `Project "${newProject.name}" created successfully`,
        "success"
      );

      // Poll for job completion, then refresh viewport
      if (job_id) {
        let jobComplete = false;
        let pollCount = 0;
        const maxPolls = 30;
        while (!jobComplete && pollCount < maxPolls) {
          try {
            const job = await BlenderAPI.fetchJobDetails(job_id);
            if (job && job.status === "completed") {
              jobComplete = true;
              // Optionally, check job.result for errors
              // Call a global or prop function to refresh the viewport here
              await refreshViewport();
            } else if (job && job.status === "failed") {
              jobComplete = true;
              showFeedback(
                `Project creation job failed: ${job.error || "Unknown error"}`,
                "error"
              );
            } else {
              await new Promise((resolve) => setTimeout(resolve, 1000));
            }
          } catch (err) {
            showFeedback(`Error polling project creation job: ${err}`, "error");
            break;
          }
          pollCount++;
        }
      }
    } catch (error) {
      showFeedback(`Error creating project: ${error}`, "error");
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  return (
    <div className="  rounded-lg shadow-sm border border-primary/20 p-4">
      {/* Tabs for Create and Load Project */}
      <Tabs defaultActiveKey="create" className="mb-4">
        <Tabs.TabPane
          tab={
            <span className="flex items-center gap-2">
              <Database className="h-4 w-4 text-accent" />
              Create Project
            </span>
          }
          key="create"
        >
          {/* Create Project Section */}
          <div className="p-3 border border-primary/20 rounded-md bg-primary/5">
            <h4 className="font-medium text-primary mb-3 flex items-center gap-2">
              <Database className="h-4 w-4 text-accent" />
              Create Project
            </h4>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-primary/70 mb-1">
                  Project Name
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 border border-primary/30 rounded-md focus:outline-none focus:ring-1 focus:ring-accent dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                  placeholder="Enter project name"
                  disabled={isLoadingProjects}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-primary/70 mb-1">
                  Description (optional)
                </label>
                <textarea
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-primary/30 rounded-md focus:outline-none focus:ring-1 focus:ring-accent dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                  placeholder="Enter project description"
                  rows={2}
                  disabled={isLoadingProjects}
                />
              </div>
              <button
                onClick={handleCreateProject}
                disabled={isLoadingProjects || !newProjectName.trim()}
                className="w-full px-3 py-2 bg-accent text-white rounded-md hover:bg-accent/80 disabled:opacity-50 disabled:cursor-not-allowed text-sm flex items-center justify-center gap-2"
              >
                <Database className="h-4 w-4" />
                Create Project
              </button>
            </div>
          </div>
        </Tabs.TabPane>
        <Tabs.TabPane
          tab={
            <span className="flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              Load Project
            </span>
          }
          key="load"
        >
          {/* Load Project Section */}
          <div className="p-3 border border-primary/20 rounded-md">
            <h4 className="font-medium text-primary mb-3 flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              Load Project
            </h4>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-primary/70 mb-1">
                  Select Project
                </label>
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full px-3 py-2 border border-primary/30 rounded-md focus:outline-none focus:ring-1 focus:ring-accent dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                  disabled={connectionStatus.status !== "success"}
                >
                  <option value="">Choose a project...</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}{" "}
                      {project.file_path
                        ? `(${project.file_path})`
                        : "(No file)"}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleLoadProject}
                disabled={
                  connectionStatus.status !== "success" ||
                  isExecutingCommand ||
                  !selectedProjectId
                }
                className="w-full px-3 py-2 bg-primary text-secondary rounded-md hover:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed text-sm flex items-center justify-center gap-2"
              >
                <Upload className="h-4 w-4" />
                Load Project
              </button>
            </div>
          </div>
        </Tabs.TabPane>
      </Tabs>

      {/* Projects List */}
      <div>
        <h4 className="font-medium text-primary mb-3">
          Recent Projects{" "}
          <button
            onClick={loadProjects}
            disabled={
              connectionStatus.status !== "success" || isLoadingProjects
            }
            className="p-2 text-primary/60 hover:text-primary hover:bg-primary/5 rounded-md transition-colors"
            title="Refresh projects"
          >
            <RefreshCw
              className={`h-4 w-4 ${isLoadingProjects ? "animate-spin" : ""}`}
            />
          </button>
        </h4>
        {isLoadingProjects ? (
          <div className="text-center text-primary/60 py-4">
            <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2" />
            Loading projects...
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center text-primary/60 py-4">
            No projects found. Please create a project in Blender first.
          </div>
        ) : (
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {projects.map((project) => (
              <div
                key={project.id}
                className="flex items-center justify-between px-2 py-1 border border-primary/10 rounded hover:bg-primary/5 text-sm"
              >
                <div className="flex-1 min-w-0 flex flex-col">
                  <div className="flex items-center gap-2 truncate">
                    <span className="font-medium text-primary truncate">
                      {project.name}
                    </span>
                    {project.file_path && (
                      <span className="text-xs bg-accent/10 text-accent px-1 rounded">
                        Saved
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-primary/50 truncate">
                    <Clock className="h-3 w-3" />
                    {formatDate(project.updated_at)}
                    {project.file_path && (
                      <span
                        className="truncate max-w-32"
                        title={project.file_path}
                      >
                        • {project.file_path}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-2">
                  <button
                    onClick={() => handleSaveProject(project.id)}
                    disabled={
                      connectionStatus.status !== "success" ||
                      isExecutingCommand
                    }
                    className="p-1 text-accent hover:text-accent/80 hover:bg-accent/10 rounded transition-colors"
                    title="Save project"
                  >
                    <Save className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() =>
                      handleDeleteProject(project.id, project.name)
                    }
                    disabled={connectionStatus.status !== "success"}
                    className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                    title="Delete project"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProjectManagerPanel;
