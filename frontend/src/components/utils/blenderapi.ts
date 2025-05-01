/**
 * BlenderLM API service
 * Handles all API interactions with the BlenderLM backend
 */

// Base URL for the FastAPI backend
const API_BASE_URL = "http://localhost:8199";

export interface ConnectionStatus {
  connected: boolean;
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

export class BlenderAPI {
  /**
   * Check connection status with Blender
   */
  static async checkConnection(): Promise<ConnectionStatus> {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      const data = await response.json();
      return {
        connected: data.blender_connected,
        error: data.error,
      };
    } catch (error) {
      return {
        connected: false,
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

    return this.executeCommand("/api/objects", params);
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

    return this.executeCommand("/api/objects", params);
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

    return this.executeCommand("/api/materials", params);
  }

  /**
   * Render the current scene
   */
  static async renderScene(): Promise<{ job_id: string }> {
    const params = {
      resolution_x: 800,
      resolution_y: 600,
    };

    return this.executeCommand("/api/render", params);
  }

  /**
   * Capture the current viewport
   */
  static async captureViewport(): Promise<{ job_id: string }> {
    const params = {
      return_base64: true,
      camera_view: false,
    };

    return this.executeCommand("/api/viewport", params);
  }

  /**
   * Get information about the current scene
   */
  static async getSceneInfo(): Promise<{ job_id: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/scene`, {
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
    return this.executeCommand("/api/code", { code });
  }

  /**
   * Clear the current scene
   */
  static async clearScene(): Promise<{ job_id: string }> {
    return this.executeCommand("/api/scene/clear", {});
  }

  /**
   * Add a camera to the scene
   */
  static async addCamera(
    params: { location?: number[]; rotation?: number[] } = {}
  ): Promise<{ job_id: string }> {
    return this.executeCommand("/api/camera", params);
  }

  /**
   * Process a natural language query using the LLM agent
   */
  static async processChat(query: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error processing chat:", error);
      throw error;
    }
  }
}

export default BlenderAPI;
