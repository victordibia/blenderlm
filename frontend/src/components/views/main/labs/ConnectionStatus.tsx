import React from "react";
import { RefreshCcw, CheckCircle, AlertCircle } from "lucide-react";
import { ConnectionStatus as ConnectionStatusType } from "../../../utils/blenderapi";

interface ConnectionStatusProps {
  connectionStatus: ConnectionStatusType;
  isCheckingConnection: boolean;
  checkConnection: () => void;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  connectionStatus,
  isCheckingConnection,
  checkConnection,
}) => {
  return (
    <div className="bg-secondary rounded-lg shadow-sm p-4 mb-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          {connectionStatus.connected ? (
            <>
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="font-medium">Connected to Blender</span>
            </>
          ) : (
            <>
              <AlertCircle className="h-5 w-5 text-red-500" />
              <span className="font-medium">Not connected to Blender</span>
            </>
          )}
        </div>
        <button
          className="flex items-center gap-1 px-3 py-1 bg-accent/10 hover:bg-accent/20 text-accent rounded-md"
          onClick={checkConnection}
          disabled={isCheckingConnection}
        >
          {isCheckingConnection ? (
            <RefreshCcw className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCcw className="h-4 w-4" />
          )}
          Check Connection
        </button>
      </div>

      {!connectionStatus.connected && (
        <div className="mt-3 p-3 bg-red-50 text-red-800 rounded-md">
          <h4 className="font-medium mb-1">Connection Failed</h4>
          <p className="text-sm mb-2">
            BlenderLM cannot connect to Blender. Please ensure:
          </p>
          <ol className="text-sm list-decimal list-inside space-y-1">
            <li>Blender is running on your system</li>
            <li>The BlenderLM add-on is installed in Blender</li>
            <li>
              The BlenderLM server is running (execute{" "}
              <code>blenderlm server</code> in terminal)
            </li>
          </ol>
          {connectionStatus.error && (
            <div className="mt-2 p-2 bg-red-100 text-red-700 text-xs rounded">
              Error details: {connectionStatus.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ConnectionStatus;
