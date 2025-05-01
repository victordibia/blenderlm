import React, { useState, useEffect } from "react";
import BlenderAPI, { Job } from "../utils/blenderapi";
import { ChevronDown, ChevronUp, RefreshCw } from "lucide-react";

interface SceneObject {
  name: string;
  type: string;
  location: number[];
}

interface SceneInfo {
  name: string;
  object_count: number;
  objects: SceneObject[];
  materials_count: number;
}

const SceneInfoPanel: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sceneInfo, setSceneInfo] = useState<SceneInfo | null>(null);
  const [jobInfo, setJobInfo] = useState<Job | null>(null);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  const fetchSceneInfo = async () => {
    setLoading(true);
    setError(null);

    try {
      // Make the initial request to get a job ID
      const response = await BlenderAPI.getSceneInfo();
      const jobId = response.job_id;

      if (!jobId) {
        throw new Error("No job ID returned from server");
      }

      // Poll for job completion
      const pollInterval = setInterval(async () => {
        try {
          const jobDetails = await BlenderAPI.fetchJobDetails(jobId);
          setJobInfo(jobDetails);

          if (!jobDetails) {
            clearInterval(pollInterval);
            setError("Failed to fetch job details");
            setLoading(false);
            return;
          }

          if (jobDetails.status === "completed" && jobDetails.result) {
            clearInterval(pollInterval);
            setSceneInfo(jobDetails.result as unknown as SceneInfo);
            setLoading(false);
          } else if (jobDetails.status === "failed") {
            clearInterval(pollInterval);
            setError(jobDetails.error || "Job failed");
            setLoading(false);
          }
        } catch (err) {
          clearInterval(pollInterval);
          setError(`Error polling job: ${err}`);
          setLoading(false);
        }
      }, 1000);

      // Cleanup function to clear interval if component unmounts
      return () => clearInterval(pollInterval);
    } catch (err) {
      setError(`Error fetching scene info: ${err}`);
      setLoading(false);
    }
  };

  // Fetch scene info when component mounts
  useEffect(() => {
    fetchSceneInfo();
  }, []);

  const objectTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "mesh":
      case "cube":
        return "📦"; // Cube emoji
      case "sphere":
        return "🔵"; // Circle emoji
      case "cylinder":
        return "🥫"; // Can emoji
      case "cone":
        return "🔺"; // Triangle emoji
      case "camera":
        return "📷"; // Camera emoji
      case "light":
      case "lamp":
        return "💡"; // Light bulb emoji
      case "empty":
        return "⭐"; // Star emoji
      default:
        return "🧩"; // Puzzle piece for unknown types
    }
  };

  return (
    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold dark:text-white">
          Scene Information
        </h2>
        <div className="flex space-x-2">
          <button
            onClick={toggleExpand}
            className="px-3 py-1 rounded text-white bg-green-500 hover:bg-green-600"
          >
            {isExpanded ? <ChevronUp /> : <ChevronDown />}
          </button>
          <button
            onClick={fetchSceneInfo}
            disabled={loading}
            className={`px-3 py-1 rounded text-white ${
              loading ? "bg-gray-400" : "bg-blue-500 hover:bg-blue-600"
            }`}
          >
            {loading ? <RefreshCw className="animate-spin" /> : <RefreshCw />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <>
          {error && (
            <div className="p-3 mb-4 text-red-700 bg-red-100 rounded dark:bg-red-900 dark:text-red-100">
              {error}
            </div>
          )}

          {loading && !error && (
            <div className="flex items-center justify-center p-6">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
              <span className="ml-2 text-gray-600 dark:text-gray-300">
                {jobInfo?.status === "processing"
                  ? "Processing scene data..."
                  : "Loading scene data..."}
              </span>
            </div>
          )}

          {sceneInfo && !loading && !error && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Scene Name
                  </p>
                  <p className="text-lg font-medium dark:text-white">
                    {sceneInfo.name}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Objects
                  </p>
                  <p className="text-lg font-medium dark:text-white">
                    {sceneInfo.object_count}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Materials
                  </p>
                  <p className="text-lg font-medium dark:text-white">
                    {sceneInfo.materials_count || 0}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Last Updated
                  </p>
                  <p className="text-lg font-medium dark:text-white">
                    {new Date().toLocaleTimeString()}
                  </p>
                </div>
              </div>

              {sceneInfo.objects && sceneInfo.objects.length > 0 ? (
                <div className="mt-6">
                  <h3 className="text-lg font-medium mb-2 dark:text-white">
                    Objects in Scene
                  </h3>
                  <div className="overflow-auto max-h-64 rounded border dark:border-gray-700">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Type
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Name
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Location
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200 dark:bg-gray-900 dark:divide-gray-700">
                        {sceneInfo.objects.map((obj, index) => (
                          <tr
                            key={index}
                            className="hover:bg-gray-50 dark:hover:bg-gray-800"
                          >
                            <td className="px-4 py-2 whitespace-nowrap">
                              <span className="mr-2">
                                {objectTypeIcon(obj.type)}
                              </span>
                              <span className="text-gray-600 dark:text-gray-300">
                                {obj.type}
                              </span>
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-gray-800 dark:text-gray-200">
                              {obj.name}
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-gray-600 dark:text-gray-300">
                              [
                              {obj.location
                                .map((val) => val.toFixed(2))
                                .join(", ")}
                              ]
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                  No objects in this scene
                </div>
              )}
            </div>
          )}

          {!sceneInfo && !loading && !error && (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              No scene information available
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SceneInfoPanel;
