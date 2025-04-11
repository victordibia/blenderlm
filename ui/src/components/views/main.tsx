import * as React from "react";

const MainView = () => {
  return (
    <div className="bg-green-500 border flex flex-col items-center justify-center h-screen bg-gray-100">
      <div className="flex flex-col items-center justify-center">
        <h1 className="text-4xl font-bold mb-4">Welcome to the Main View</h1>
        <p className="text-lg mb-2">This is the main content area.</p>
      </div>
    </div>
  );
};

export default MainView;
