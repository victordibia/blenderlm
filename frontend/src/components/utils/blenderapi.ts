/**
 * BlenderLM API service
 * Handles all API interactions with the BlenderLM backend
 */

// Base URL for the FastAPI backend
const API_BASE_URL = "http://localhost:8199";

export interface ConnectionStatus {
  status: "fetching" | "success" | "failed";
  error?: string;
}

export interface BlenderTool {
  name: string;
  description: string;
  parameters: Record<string, string>;
  endpoint: string;
}

export interface Job {
  id: string;
  command_type: string;
  params: Record<string, any>;
  status: "pending" | "processing" | "completed" | "failed";
  result?: Record<string, any>;
  error?: string;
  created_at: number;
  completed_at?: number;
}

export interface ProjectInfo {
  id: string;
  name: string;
  description?: string;
  file_path?: string;
  status: "active" | "archived";
  created_at: number;
  updated_at: number;
  last_opened_at?: number;
  metadata?: Record<string, any>;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  file_path?: string;
  metadata?: Record<string, any>;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  file_path?: string;
  status?: "active" | "archived";
  metadata?: Record<string, any>;
}

export interface LoadProjectRequest {
  project_id?: string;
  file_path?: string;
}

export interface SaveProjectRequest {
  project_id: string;
  file_path?: string;
  create_backup?: boolean;
}

export interface ProjectListResponse {
  projects: ProjectInfo[];
  total_count: number;
}

export class BlenderAPI {
  /**
   * Check connection status with Blender
   */
  static async checkConnection(): Promise<ConnectionStatus> {
    // Implicitly, the status is 'fetching' when this function is called.
    // The calling component should manage the 'fetching' state before calling this.
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) {
        // Handle HTTP errors like 500, 404 etc.
        const errorData = await response.text(); // or response.json() if the error is structured
        return {
          status: "failed",
          error: `API request failed: ${response.status} ${response.statusText}. ${errorData}`,
        };
      }
      const data = await response.json();
      if (data.blender_connected) {
        return {
          status: "success",
        };
      } else {
        return {
          status: "failed",
          error: data.error || "Blender not connected.",
        };
      }
    } catch (error) {
      return {
        status: "failed",
        error: `Cannot connect to BlenderLM API: ${error}`,
      };
    }
  }

  /**
   * Fetch available tools from the API
   */
  static async fetchTools(): Promise<BlenderTool[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/tools`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error fetching tools:", error);
      return [];
    }
  }

  /**
   * Fetch all jobs from the API
   */
  static async fetchJobs(): Promise<Job[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/jobs`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error fetching jobs:", error);
      return [];
    }
  }

  /**
   * Fetch details for a specific job
   */
  static async fetchJobDetails(jobId: string): Promise<Job | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`Error fetching job ${jobId}:`, error);
      return null;
    }
  }

  /**
   * Execute a Blender command via the API
   */
  static async executeCommand(
    endpoint: string,
    params: any
  ): Promise<{ job_id: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(params),
      });

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error executing command:", error);
      throw error;
    }
  }

  /**
   * Add a random sphere to the scene
   */
  static async addRandomSphere(): Promise<{ job_id: string }> {
    const x = Math.random() * 4 - 2;
    const y = Math.random() * 4 - 2;
    const z = Math.random() * 2;
    const scale = 0.5 + Math.random() * 0.5;

    // Generate a random color
    const r = Math.random();
    const g = Math.random();
    const b = Math.random();

    const params = {
      type: "SPHERE",
      name: `Sphere_${Math.floor(Math.random() * 1000)}`,
      location: [x, y, z],
      scale: [scale, scale, scale],
      color: [r, g, b, 1.0],
    };

    return this.executeCommand("/api/blender/objects", params);
  }

  /**
   * Add a random cube to the scene
   */
  static async addRandomCube(): Promise<{ job_id: string }> {
    const x = Math.random() * 4 - 2;
    const y = Math.random() * 4 - 2;
    const z = Math.random() * 2;
    const scale = 0.5 + Math.random() * 0.5;

    // Generate a random color
    const r = Math.random();
    const g = Math.random();
    const b = Math.random();

    const params = {
      type: "CUBE",
      name: `Cube_${Math.floor(Math.random() * 1000)}`,
      location: [x, y, z],
      scale: [scale, scale, scale],
      color: [r, g, b, 1.0],
    };

    return this.executeCommand("/api/blender/objects", params);
  }

  /**
   * Apply a random material to an object
   */
  static async addRandomMaterial(): Promise<{ job_id: string }> {
    const r = Math.random();
    const g = Math.random();
    const b = Math.random();

    const params = {
      object_name: "Sphere_" + Math.floor(Math.random() * 1000),
      material_name: `Material_${Math.floor(Math.random() * 1000)}`,
      color: [r, g, b, 1.0],
    };

    return this.executeCommand("/api/blender/materials", params);
  }

  /**
   * Render the current scene
   */
  static async renderScene(): Promise<{ job_id: string }> {
    const params = {
      resolution_x: 800,
      resolution_y: 600,
    };

    return this.executeCommand("/api/blender/render", params);
  }

  /**
   * Capture the current viewport
   */
  static async captureViewport(): Promise<{ job_id: string }> {
    const params = {
      return_base64: true,
      camera_view: false,
    };

    return this.executeCommand("/api/blender/viewport", params);
  }

  /**
   * Get information about the current scene
   */
  static async getSceneInfo(): Promise<{ job_id: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/blender/scene`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error getting scene info:", error);
      throw error;
    }
  }

  /**
   * Execute custom Python code in Blender
   */
  static async executeCode(code: string): Promise<{ job_id: string }> {
    return this.executeCommand("/api/blender/code", { code });
  }

  /**
   * Clear the current scene
   */
  static async clearScene(): Promise<{ job_id: string }> {
    return this.executeCommand("/api/blender/scene/clear", {});
  }

  /**
   * Add a camera to the scene
   */
  static async addCamera(
    params: { location?: number[]; rotation?: number[] } = {}
  ): Promise<{ job_id: string }> {
    return this.executeCommand("/api/blender/camera", params);
  }

  /**
   * Stream chat responses from the API using WebSocket.
   */
  static streamChatWS(
    content: any[] | string,
    onMessage: (msg: any) => void,
    onError?: (err: any) => void
  ): { ws: WebSocket; sendCancel: () => void } {
    const ws = new WebSocket("ws://localhost:8199/api/blender/ws/chat");
    ws.onopen = () => {
      // Send as { type: 'start', content } for multimodal
      ws.send(JSON.stringify({ type: "start", content }));
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (err) {
        if (onError) onError(err);
      }
    };
    ws.onerror = (err) => {
      if (onError) onError(err);
      ws.close();
    };
    return {
      ws,
      sendCancel: () =>
        ws.readyState === 1 && ws.send(JSON.stringify({ type: "cancel" })),
    };
  }

  // =============================================================================
  // PROJECT MANAGEMENT METHODS
  // =============================================================================

  /**
   * List all projects
   */
  static async listProjects(
    status?: string,
    limit: number = 50
  ): Promise<ProjectListResponse> {
    try {
      const params = new URLSearchParams();
      if (status) params.append("status", status);
      params.append("limit", limit.toString());

      const response = await fetch(`${API_BASE_URL}/api/projects?${params}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error listing projects:", error);
      throw error;
    }
  }

  /**
   * Create a new project
   */
  static async createProject(
    request: CreateProjectRequest
  ): Promise<{ project: ProjectInfo; job_id: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/projects`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error creating project:", error);
      throw error;
    }
  }

  /**
   * Get a specific project by ID
   */
  static async getProject(projectId: string): Promise<ProjectInfo> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/projects/${projectId}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error getting project:", error);
      throw error;
    }
  }

  /**
   * Update a project
   */
  static async updateProject(
    projectId: string,
    request: UpdateProjectRequest
  ): Promise<ProjectInfo> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/projects/${projectId}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(request),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error updating project:", error);
      throw error;
    }
  }

  /**
   * Delete a project
   */
  static async deleteProject(projectId: string): Promise<{ message: string }> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/projects/${projectId}`,
        {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error deleting project:", error);
      throw error;
    }
  }

  /**
   * Load a project (.blend file)
   */
  static async loadProject(request: LoadProjectRequest): Promise<{
    project_id?: string;
    job_id: string;
    file_path: string;
    message: string;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/projects/load`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error loading project:", error);
      throw error;
    }
  }

  /**
   * Save current project
   */
  static async saveProject(request: SaveProjectRequest): Promise<{
    project_id: string;
    job_id: string;
    file_path: string;
    message: string;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/projects/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error saving project:", error);
      throw error;
    }
  }

  /**
   * Get information about the current Blender project
   */
  static async getCurrentProjectInfo(): Promise<{ job_id: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/projects/current`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error getting current project info:", error);
      throw error;
    }
  }

  /**
   * List jobs for a specific project
   */
  static async listProjectJobs(
    projectId: string,
    limit: number = 50
  ): Promise<Job[]> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/projects/${projectId}/jobs?limit=${limit}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error listing project jobs:", error);
      throw error;
    }
  }
}

export default BlenderAPI;
