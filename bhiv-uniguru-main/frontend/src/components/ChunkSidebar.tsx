// // import React from "react";

// // interface ChunkSidebarProps {
// //   open: boolean;
// //   onClose: () => void;
// //   chunks: Array<{ file: string; content: string }>;
// // }

// // const ChunkSidebar: React.FC<ChunkSidebarProps> = ({ open, onClose, chunks }) => {
// //   return (
// //     <div
// //       className={`fixed top-0 left-0 h-full w-80 bg-white dark:bg-gray-900 shadow-2xl z-50 transform transition-transform duration-300 ${open ? "translate-x-0" : "-translate-x-full"}`}
// //       style={{ boxShadow: open ? "2px 0 16px rgba(0,0,0,0.2)" : "none" }}
// //     >
// //       <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
// //         <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">RAG Chunks</h2>
// //         <button onClick={onClose} className="text-gray-500 hover:text-red-500 text-xl">&times;</button>
// //       </div>
// //       <div className="p-4 overflow-y-auto h-[calc(100%-56px)]">
// //         {chunks.length === 0 ? (
// //           <div className="text-gray-400 text-center">No chunks found.</div>
// //         ) : (
// //           chunks.map((chunk, idx) => (
// //             <div key={idx} className="mb-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700">
// //               <div className="font-bold text-blue-700 dark:text-blue-200 mb-1">{chunk.file || "Unknown File"}</div>
// //               <div className="text-gray-700 dark:text-gray-100 whitespace-pre-wrap text-sm">{chunk.content}</div>
// //             </div>
// //           ))
// //         )}
// //       </div>
// //     </div>
// //   );
// // };

// // export default ChunkSidebar;


// import React from "react";

// interface ChunkSidebarProps {
//   open: boolean;
//   onClose: () => void;
//   chunks: Array<{ index: number; file: string; score: number; content: string }>;
// }

// const ChunkSidebar: React.FC<ChunkSidebarProps> = ({ open, onClose, chunks }) => {
//   return (
//     <div
//       className={`fixed top-0 left-0 h-full w-80 bg-white dark:bg-gray-900 shadow-2xl z-50 transform transition-transform duration-300 ${open ? "translate-x-0" : "-translate-x-full"}`}
//       style={{ boxShadow: open ? "2px 0 16px rgba(0,0,0,0.2)" : "none" }}
//     >
//       <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
//         <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Retrieved Chunks</h2>
//         <button onClick={onClose} className="text-gray-500 hover:text-red-500 text-xl">&times;</button>
//       </div>
//       <div className="p-4 overflow-y-auto h-[calc(100%-56px)]">
//         {chunks.length === 0 ? (
//           <div className="text-gray-400 text-center">No chunks found.</div>
//         ) : (
//           chunks.map((chunk, idx) => (
//             <div key={idx} className="mb-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700">
//               <div className="font-bold text-blue-700 dark:text-blue-200 mb-1">
//                 Chunk {chunk.index} - {chunk.file || "Unknown File"}
//               </div>
//               <div className="text-gray-600 dark:text-gray-300 text-sm mb-1">
//                 Score: {chunk.score ? chunk.score.toFixed(4) : 'N/A'}
//               </div>
//               <div className="text-gray-700 dark:text-gray-100 whitespace-pre-wrap text-sm">
//                 {chunk.content}
//               </div>
//             </div>
//           ))
//         )}
//       </div>
//     </div>
//   );
// };

// export default ChunkSidebar;


// import React from "react";
// import toast from "react-hot-toast";

// interface ChunkSidebarProps {
//   open: boolean;
//   onClose: () => void;
//   chunks: Array<{ index: number; file: string; score: number; content: string }>;
// }

// const ChunkSidebar: React.FC<ChunkSidebarProps> = ({ open, onClose, chunks }) => {
//   const handleChunkClick = (chunk: { index: number; file: string; score: number; content: string }) => {
//     console.log("Clicked chunk:", chunk);
//     // Add your desired action here (e.g., copy to clipboard, open in new tab, etc.)
//     toast.success(`Selected chunk ${chunk.index} from ${chunk.file}`, {
//       duration: 2000,
//       icon: '👆'
//     });
//   };

//   return (
//     <div
//       className={`fixed top-0 left-0 h-full w-80 bg-white dark:bg-gray-900 shadow-lg z-50 transform transition-transform duration-300 ${open ? "translate-x-0" : "-translate-x-full"}`}
//       style={{ boxShadow: open ? "2px 0 16px rgba(0,0,0,0.2)" : "none" }}
//     >
//       <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
//         <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Searched Chunks</h2>
//         <button onClick={onClose} className="text-gray-500 hover:text-red-500 text-xl">&times;</button>
//       </div>
//       <div className="p-4 overflow-y-auto h-[calc(100%-56px)]">
//         {chunks.length === 0 ? (
//           <div className="text-gray-400 text-center py-4">No chunks found.</div>
//         ) : (
//           <ul className="space-y-2">
//             {chunks.map((chunk, idx) => (
//               <li
//                 key={idx}
//                 onClick={() => handleChunkClick(chunk)}
//                 className="cursor-pointer p-3 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200"
//               >
//                 <div className="font-semibold text-blue-600 dark:text-blue-400 mb-1">
//                   Chunk {chunk.index} - {chunk.file || "Unknown File"}
//                 </div>
//                 <div className="text-gray-600 dark:text-gray-300 text-sm mb-1">
//                   Score: {chunk.score ? chunk.score.toFixed(4) : 'N/A'}
//                 </div>
//                 <div className="text-gray-700 dark:text-gray-300 text-sm line-clamp-3">
//                   {chunk.content}
//                 </div>
//               </li>
//             ))}
//           </ul>
//         )}
//       </div>
//     </div>
//   );
// };

// export default ChunkSidebar;

// import React from "react";

// interface ChunkSidebarProps {
//   open: boolean;
//   onClose: () => void;
//   chunks: Array<{ index: number; file: string; score: number; content: string }>;
//   selectedChunk: { index: number; file: string; score: number; content: string } | null;
//   setSelectedChunk: (chunk: { index: number; file: string; score: number; content: string } | null) => void;
// }

// export 
// const ChunkSidebar: React.FC<ChunkSidebarProps> = ({ open, onClose, chunks, selectedChunk, setSelectedChunk }) => {
//   const handleChunkClick = (chunk: { index: number; file: string; score: number; content: string }) => {
//     setSelectedChunk(chunk);
//   };

//   const handleCloseDrawer = () => {
//     setSelectedChunk(null);
//   };

//   return (
//     <div
//       className={`fixed top-0 right-0 h-full w-96 bg-gray-800 text-white shadow-lg z-50 transform transition-transform duration-300 ${open ? "translate-x-0" : "translate-x-full"}`}
//       style={{ boxShadow: open ? "-2px 0 16px rgba(0,0,0,0.3)" : "none" }}
//     >
//       <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-900">
//         <h2 className="text-lg font-semibold">Searched Chunks</h2>
//         <button onClick={onClose} className="text-gray-400 hover:text-red-500 text-xl">&times;</button>
//       </div>
//       <div className="p-4 overflow-y-auto h-[calc(100%-56px)]">
//         {chunks.length === 0 ? (
//           <div className="text-gray-500 text-center py-4">No chunks found.</div>
//         ) : (
//           <ul className="space-y-2">
//             {chunks.map((chunk, idx) => (
//               <li
//                 key={idx}
//                 onClick={() => handleChunkClick(chunk)}
//                 className="cursor-pointer p-3 rounded-lg bg-gray-700 border border-gray-600 hover:bg-gray-600 transition-colors duration-200"
//               >
//                 <div className="font-semibold text-blue-300 mb-1">
//                   Chunk {chunk.index} - {chunk.file || "Unknown File"}
//                 </div>
//                 <div className="text-gray-400 text-sm mb-1">
//                   Score: {chunk.score ? chunk.score.toFixed(4) : 'N/A'}
//                 </div>
//                 <div className="text-gray-300 text-sm line-clamp-3">
//                   {chunk.content}
//                 </div>
//               </li>
//             ))}
//           </ul>
//         )}
//         {selectedChunk && (
//           <div className="fixed top-0 right-0 w-96 h-full bg-gray-900 text-white shadow-lg z-60 transform transition-transform duration-300 translate-x-0 p-4 overflow-y-auto">
//             <div className="flex items-center justify-between border-b border-gray-700 pb-2 mb-4">
//               <h3 className="text-lg font-semibold">Chunk Details</h3>
//               <button onClick={handleCloseDrawer} className="text-gray-400 hover:text-red-500 text-xl">&times;</button>
//             </div>
//             <div>
//               <div className="font-semibold text-blue-300 mb-1">
//                 Chunk {selectedChunk.index} - {selectedChunk.file || "Unknown File"}
//               </div>
//               <div className="text-gray-400 text-sm mb-1">
//                 Score: {selectedChunk.score ? selectedChunk.score.toFixed(4) : 'N/A'}
//               </div>
//               <div className="text-gray-300 whitespace-pre-wrap">
//                 {selectedChunk.content}
//               </div>
//             </div>
//           </div>
//         )}
//       </div>
//     </div>
//   );
// };

// export default ChunkSidebar;


import React from "react";

interface ChunkSidebarProps {
  open: boolean;
  onClose: () => void;
  chunks: Array<{ index: number; file: string; score: number; content: string }>;
  selectedChunk: { index: number; file: string; score: number; content: string } | null;
  setSelectedChunk: (chunk: { index: number; file: string; score: number; content: string } | null) => void;
}

const ChunkSidebar: React.FC<ChunkSidebarProps> = ({ open, onClose, chunks, selectedChunk, setSelectedChunk }) => {
  const handleChunkClick = (chunk: { index: number; file: string; score: number; content: string }) => {
    setSelectedChunk(chunk);
  };

  const handleCloseDrawer = () => {
    setSelectedChunk(null);
  };

  return (
    <div
      className={`fixed top-0 right-0 h-full w-96 bg-gray-800 text-white shadow-lg z-50 transform transition-transform duration-300 ${open ? "translate-x-0" : "translate-x-full"} chunk-sidebar`}
      style={{ boxShadow: open ? "-2px 0 16px rgba(0,0,0,0.3)" : "none" }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-900">
        <h2 className="text-lg font-semibold">Searched Chunks</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-red-500 text-xl">&times;</button>
      </div>
      <div className="p-4 overflow-y-auto h-[calc(100%-56px)]">
        {chunks.length === 0 ? (
          <div className="text-gray-500 text-center py-4">No chunks found.</div>
        ) : (
          <ul className="space-y-2">
            {chunks.map((chunk, idx) => (
              <li
                key={idx}
                onClick={() => handleChunkClick(chunk)}
                className="cursor-pointer p-3 rounded-lg bg-gray-700 border border-gray-600 hover:bg-gray-600 transition-colors duration-200"
              >
                <div className="font-semibold text-blue-300 mb-1">
                  Chunk {chunk.index} - {chunk.file || "Unknown File"}
                </div>
                <div className="text-gray-400 text-sm mb-1">
                  Score: {chunk.score ? chunk.score.toFixed(4) : 'N/A'}
                </div>
                <div className="text-gray-300 text-sm line-clamp-3">
                  {chunk.content}
                </div>
              </li>
            ))}
          </ul>
        )}
        {selectedChunk && (
          <div className="fixed top-0 right-0 w-96 h-full bg-gray-900 text-white shadow-lg z-60 transform transition-transform duration-300 translate-x-0 p-4 overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-700 pb-2 mb-4">
              <h3 className="text-lg font-semibold">Chunk Details</h3>
              <button onClick={handleCloseDrawer} className="text-gray-400 hover:text-red-500 text-xl">&times;</button>
            </div>
            <div>
              <div className="font-semibold text-blue-300 mb-1">
                Chunk {selectedChunk.index} - {selectedChunk.file || "Unknown File"}
              </div>
              <div className="text-gray-400 text-sm mb-1">
                Score: {selectedChunk.score ? selectedChunk.score.toFixed(4) : 'N/A'}
              </div>
              <div className="text-gray-300 whitespace-pre-wrap">
                {selectedChunk.content}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChunkSidebar;