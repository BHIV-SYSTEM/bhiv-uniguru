// import { useState, useRef, useEffect } from "react";
// import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
// import { faCopy, faVolumeHigh, faPause, faPlay, faStop, faDatabase } from "@fortawesome/free-solid-svg-icons";
// import uniguru from "../assets/uni-logo.png";
// import userimage from "../assets/userimage.png";
// import guruLogo from "../assets/guru.png";

// // import BubblyButton from "./BubblyButton";

// import EnhancedChatInput from "./EnhancedChatInput";
// import LoadingSpinner from "./LoadingSpinner";
// import ChunkSidebar from "./ChunkSidebar";
// // import { useNavigate } from "react-router-dom";
// import toast from "react-hot-toast";
// import { useAuth } from "../context/AuthContext";
// import { useChat } from "../context/ChatContext";
// import { useGuru } from "../context/GuruContext";
// import { sendChatRequest, getChatSessionById, scanImageText, readPdf } from "../helpers/api-communicator";

// interface Message {
//   text: string;
//   sender: "user" | "bot";
//   timestamp?: Date;
//   isLoading?: boolean;
//   retrieved_chunks?: Array<{ file: string; content: string }>;
// }

// const ChatContainer: React.FC = () => {
//   const { user } = useAuth();
//   const { currentChatId } = useChat();
//   const { selectedGuru } = useGuru();
//   interface FileAttachment {
//     id: string;
//     file: File;
//     type: 'image' | 'pdf' | 'document';
//     preview?: string;
//   }

//   const [messages, setMessages] = useState<Message[]>([]);
//   const [message, setMessage] = useState<string>("");
//   const [attachments, setAttachments] = useState<FileAttachment[]>([]);
//   const [isLoading, setIsLoading] = useState(false);
//   const [isPlaying, setIsPlaying] = useState(false);
//   const [, setCurrentUtterance] = useState<SpeechSynthesisUtterance | null>(null);
//   const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
//   // Sidebar state
//   const [sidebarOpen, setSidebarOpen] = useState(false);
//   const [sidebarChunks, setSidebarChunks] = useState<Array<{ file: string; content: string }>>([]);

//   const messagesEndRef = useRef<HTMLDivElement | null>(null);
//   const messagesContainerRef = useRef<HTMLDivElement | null>(null);
//   const textareaRef = useRef<HTMLTextAreaElement | null>(null);
//   // const navigate = useNavigate();

//   const scrollToBottom = () => {
//     if (messagesEndRef.current) {
//       messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
//     }
//   };

//   // Always scroll to bottom for all messages (new and loaded)
//   useEffect(() => {
//     // Always scroll to bottom to show the most recent messages
//     scrollToBottom();
//   }, [messages]);

//   // Cleanup audio on component unmount
//   useEffect(() => {
//     return () => {
//       if ('speechSynthesis' in window) {
//         window.speechSynthesis.cancel();
//       }
//     };
//   }, []);

//   // Keyboard shortcuts for audio control
//   useEffect(() => {
//     const handleKeyDown = (event: KeyboardEvent) => {
//       if (event.key === 'Escape' && isPlaying) {
//         handleStopAudio();
//       }
//     };

//     document.addEventListener('keydown', handleKeyDown);
//     return () => {
//       document.removeEventListener('keydown', handleKeyDown);
//     };
//   }, [isPlaying]);

//   // Clear messages when guru changes
//   useEffect(() => {
//     setMessages([]);
//     console.log(`Cleared messages due to guru change: ${selectedGuru?.name || 'None'}`);
//   }, [selectedGuru]);

//   // Load chat history when current chat changes
//   useEffect(() => {
//     const loadChatHistory = async () => {
//       if (currentChatId) {
//         try {
//           console.log(`Loading chat history for chat ID: ${currentChatId}`);
//           const response = await getChatSessionById(currentChatId);
//           const chatMessages = response.chat.messages || [];
//           const formattedMessages = chatMessages.map((msg: any) => ({
//             text: msg.content,
//             sender: msg.sender === 'user' ? 'user' : 'bot',
//             timestamp: new Date(msg.timestamp),
//             // Map retrieved_chunks from metadata if present
//             retrieved_chunks: msg.metadata && Array.isArray(msg.metadata.retrieved_chunks)
//               ? msg.metadata.retrieved_chunks
//               : []
//           }));
//           setMessages(formattedMessages);
//           console.log(`Loaded ${formattedMessages.length} messages for chat ${currentChatId}`);

//           if (formattedMessages.length > 0) {
//             toast.success(`Loaded ${formattedMessages.length} previous messages`, {
//               duration: 2000,
//               icon: '💬'
//             });
//           }
//         } catch (error) {
//           console.error('Error loading chat history:', error);
//           toast.error("Failed to load chat history", {
//             duration: 2000,
//             icon: '⚠️'
//           });
//           setMessages([]);
//         }
//       } else {
//         // No current chat selected, clear messages
//         console.log('No current chat selected, clearing messages');
//         setMessages([]);
//       }
//     };

//     loadChatHistory();
//   }, [currentChatId]); // Only depend on currentChatId for proper isolation

//   const handleSendMessage = async () => {
//     if ((!message.trim() && attachments.length === 0) || !selectedGuru || !user || isLoading) {
//       return;
//     }

//     const userMessage = message.trim();
//     setMessage("");
//     setIsLoading(true);

//     // Process attachments first
//     const attachmentContent = await processAttachments();
//     const fullMessage = userMessage + attachmentContent;

//     // Clear attachments after processing
//     setAttachments([]);

//     // Add user message immediately (show original message without attachment content)
//     const newUserMessage: Message = {
//       text: userMessage + (attachments.length > 0 ? ` [${attachments.length} file(s) attached]` : ''),
//       sender: "user",
//       timestamp: new Date()
//     };
//     setMessages(prev => [...prev, newUserMessage]);

//     // Add loading message for AI response
//     const loadingMessage: Message = {
//       text: "Thinking...",
//       sender: "bot",
//       timestamp: new Date(),
//       isLoading: true
//     };
//     setMessages(prev => [...prev, loadingMessage]);

//     // Reset textarea height
//     const textarea = document.querySelector("textarea");
//     if (textarea) {
//       textarea.style.height = "auto";
//     }

//     try {
//       // Prepare last 3 messages as context (excluding loading message)
//       const context = messages
//         .slice(-3)
//         .filter((msg) => !msg.isLoading)
//         .map((msg) => ({
//           sender: msg.sender,
//           content: msg.text,
//           timestamp: msg.timestamp ? new Date(msg.timestamp).toISOString() : new Date().toISOString(),
//         }));

//       // Send message to backend with context
//       const response = await sendChatRequest(
//         fullMessage,
//         selectedGuru.id,
//         user.id,
//         currentChatId || undefined,
//         context
//       );

//       // Remove loading message and add AI response
//       if (response.aiResponse) {
//         const botMessage: Message = {
//           text: response.aiResponse.content,
//           sender: "bot",
//           timestamp: new Date(),
//           retrieved_chunks: response.aiResponse.metadata?.retrieved_chunks || []
//         };

//         // Replace loading message with actual response
//         setMessages(prev => {
//           const newMessages = [...prev];
//           // Remove the loading message (last message)
//           newMessages.pop();
//           // Add the actual response
//           newMessages.push(botMessage);
//           return newMessages;
//         });

//         // If this created a new chat, update the current chat ID
//         if (response.chat && response.chat.id && !currentChatId) {
//           console.log(`New chat created with ID: ${response.chat.id}`);
//           // The ChatContext should handle this automatically, but we can log it
//         }
//       }
//     } catch (error) {
//       console.error('Error sending message:', error);
//       toast.error("Failed to send message. Please try again.", {
//         duration: 3000,
//         icon: '❌'
//       });

//       // Replace loading message with error message
//       const errorMessage: Message = {
//         text: "Sorry, I'm having trouble responding right now. Please try again.",
//         sender: "bot",
//         timestamp: new Date()
//       };

//       setMessages(prev => {
//         const newMessages = [...prev];
//         // Remove the loading message (last message)
//         newMessages.pop();
//         // Add the error message
//         newMessages.push(errorMessage);
//         return newMessages;
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };
  


//   const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
//     if (e.key === "Enter" && !e.shiftKey) {
//       e.preventDefault();
//       handleSendMessage();
//     }
//   };

//   // Copy message text to clipboard
//   const handleCopyMessage = async (text: string) => {
//     try {
//       await navigator.clipboard.writeText(text);
//       toast.success("Message copied to clipboard!", {
//         duration: 2000,
//         icon: '📋'
//       });
//     } catch (err) {
//       console.error('Failed to copy text: ', err);
//       // Fallback for older browsers
//       const textArea = document.createElement('textarea');
//       textArea.value = text;
//       document.body.appendChild(textArea);
//       textArea.select();
//       document.execCommand('copy');
//       document.body.removeChild(textArea);
//       toast.success("Message copied to clipboard!", {
//         duration: 2000,
//         icon: '📋'
//       });
//     }
//   };

//   // Text-to-speech functionality
//   const handleTextToSpeech = (text: string, messageIndex: number) => {
//     if ('speechSynthesis' in window) {
//       // If already playing this message, pause/resume
//       if (isPlaying && playingMessageIndex === messageIndex) {
//         if (window.speechSynthesis.paused) {
//           window.speechSynthesis.resume();
//           toast.success("Audio resumed", {
//             duration: 1000,
//             icon: '▶️'
//           });
//         } else {
//           window.speechSynthesis.pause();
//           toast.success("Audio paused", {
//             duration: 1000,
//             icon: '⏸️'
//           });
//         }
//         return;
//       }

//       // Cancel any ongoing speech
//       window.speechSynthesis.cancel();
//       setIsPlaying(false);
//       setCurrentUtterance(null);
//       setPlayingMessageIndex(null);

//       const utterance = new SpeechSynthesisUtterance(text);
//       utterance.rate = 0.9;
//       utterance.pitch = 1;
//       utterance.volume = 0.8;

//       // Try to use a more natural voice if available
//       const voices = window.speechSynthesis.getVoices();
//       const preferredVoice = voices.find(voice =>
//         voice.name.includes('Google') ||
//         voice.name.includes('Microsoft') ||
//         voice.lang.startsWith('en')
//       );

//       if (preferredVoice) {
//         utterance.voice = preferredVoice;
//       }

//       utterance.onstart = () => {
//         setIsPlaying(true);
//         setCurrentUtterance(utterance);
//         setPlayingMessageIndex(messageIndex);
//         toast.success("Playing audio...", {
//           duration: 1500,
//           icon: '🔊'
//         });
//       };

//       utterance.onend = () => {
//         setIsPlaying(false);
//         setCurrentUtterance(null);
//         setPlayingMessageIndex(null);
//         toast.success("Audio finished", {
//           duration: 1000,
//           icon: '✅'
//         });
//       };

//       utterance.onerror = (_event) => {
//         setIsPlaying(false);
//         setCurrentUtterance(null);
//         setPlayingMessageIndex(null);
//         toast.error("Failed to play audio", {
//           duration: 2000,
//           icon: '❌'
//         });
//       };

//       window.speechSynthesis.speak(utterance);
//     } else {
//       toast.error("Text-to-speech not supported in this browser", {
//         duration: 3000,
//         icon: '❌'
//       });
//     }
//   };

//   // Stop audio playback
//   const handleStopAudio = () => {
//     if ('speechSynthesis' in window) {
//       window.speechSynthesis.cancel();
//       setIsPlaying(false);
//       setCurrentUtterance(null);
//       setPlayingMessageIndex(null);
//       toast.success("Audio stopped", {
//         duration: 1000,
//         icon: '⏹️'
//       });
//     }
//   };

//   // Handle file upload (add to attachments for preview)
//   const handleFileUpload = async (file: File) => {
//     const fileType = file.type;
//     const fileName = file.name.toLowerCase();

//     // Determine file type
//     let type: 'image' | 'pdf' | 'document' = 'document';
//     if (fileType.startsWith('image/')) {
//       type = 'image';
//     } else if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
//       type = 'pdf';
//     }

//     // Create attachment object
//     const attachment: FileAttachment = {
//       id: Date.now().toString(),
//       file,
//       type,
//     };

//     // Generate preview for images
//     if (type === 'image') {
//       const reader = new FileReader();
//       reader.onload = (e) => {
//         attachment.preview = e.target?.result as string;
//         setAttachments(prev => [...prev, attachment]);
//       };
//       reader.readAsDataURL(file);
//     } else {
//       setAttachments(prev => [...prev, attachment]);
//     }

//     toast.success(`${type === 'image' ? 'Image' : type === 'pdf' ? 'PDF' : 'File'} attached successfully!`, {
//       duration: 2000,
//       icon: type === 'image' ? '🖼️' : type === 'pdf' ? '📄' : '📎'
//     });
//   };

//   // Remove attachment
//   const handleRemoveAttachment = (id: string) => {
//     setAttachments(prev => prev.filter(att => att.id !== id));
//     toast.success("File removed", {
//       duration: 1500,
//       icon: '🗑️'
//     });
//   };

//   // Process attachments when sending message
//   const processAttachments = async (): Promise<string> => {
//     if (attachments.length === 0) return '';

//     let extractedContent = '';

//     for (const attachment of attachments) {
//       try {
//         if (attachment.type === 'image') {
//           toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
//           const result = await scanImageText(attachment.file);
//           if (result.extractedText) {
//             extractedContent += `\n\n[Image: ${attachment.file.name}]\n${result.extractedText}`;
//             toast.success(`Image processed successfully!`, { id: `process-${attachment.id}`, icon: '🖼️' });
//           }
//         } else if (attachment.type === 'pdf') {
//           toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
//           const result = await readPdf(attachment.file);
//           if (result.extractedText) {
//             extractedContent += `\n\n[PDF: ${attachment.file.name}]\n${result.extractedText}`;
//             toast.success(`PDF processed successfully!`, { id: `process-${attachment.id}`, icon: '📄' });
//           }
//         }
//       } catch (error) {
//         console.error(`Error processing ${attachment.file.name}:`, error);
//         toast.error(`Failed to process ${attachment.file.name}`, { id: `process-${attachment.id}` });
//       }
//     }

//     return extractedContent;
//   };

//   return (
//     <div
//       className="chat-container flex flex-col text-white transition-all duration-300 relative overflow-hidden"
//       style={{
//         width: "100%",
//       }}
//     >




//       {/* Selected Guru Display */}
//       {selectedGuru && (
//         <div className="w-full flex justify-center px-3 sm:px-4 pt-4 pb-3 flex-shrink-0">
//           <div className="max-w-md w-full bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10">
//             <div className="flex items-center justify-center gap-3">
//               {/* Simple Avatar */}
//               <div className="relative">
//                 <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-purple-600 rounded-full flex items-center justify-center">
//                   <img src={guruLogo} alt="Guru" className="w-6 h-6" />
//                 </div>
//                 {/* Simple online dot */}
//                 <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-900"></div>
//               </div>

//               {/* Centered Guru info */}
//               <div className="text-center">
//                 <h3 className="text-white font-medium text-sm">
//                   {selectedGuru.name}
//                 </h3>
//                 <p className="text-gray-400 text-xs">
//                   {selectedGuru.subject}
//                 </p>
//               </div>

//               {/* Simple status */}
//               <div className="text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded-full">
//                 Active
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Audio Status Indicator */}
//       {isPlaying && (
//         <div className="w-full flex justify-center px-3 sm:px-4 pb-3 flex-shrink-0">
//           <div className="max-w-sm w-full bg-green-500/10 backdrop-blur-sm rounded-lg p-3 border border-green-400/20">
//             <div className="flex items-center justify-center gap-3">
//               <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
//               <span className="text-green-300 text-sm">Audio playing...</span>
//               <div className="flex items-center space-x-2">
//                 <FontAwesomeIcon
//                   icon={window.speechSynthesis?.paused ? faPlay : faPause}
//                   className="text-green-400 hover:text-green-300 cursor-pointer transition-colors text-sm"
//                   onClick={() => {
//                     if (playingMessageIndex !== null) {
//                       const message = messages[playingMessageIndex];
//                       if (message) {
//                         handleTextToSpeech(message.text, playingMessageIndex);
//                       }
//                     }
//                   }}
//                   title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
//                 />
//                 <FontAwesomeIcon
//                   icon={faStop}
//                   className="text-red-400 hover:text-red-300 cursor-pointer transition-colors text-sm"
//                   onClick={handleStopAudio}
//                   title="Stop audio"
//                 />
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Chat messages */}
//       <div
//         ref={messagesContainerRef}
//         className={`chat-messages-area flex-1 w-full max-w-6xl flex px-4 sm:px-8 py-2 chat-messages-container mx-auto ${
//           messages.length > 0 ? 'flex-col gap-3 sm:gap-4' : 'items-center justify-center lg:min-h-[60vh]'
//         }`}
//         style={{
//           minHeight: 0, // Important for flex-1 to work with overflow
//           overflowY: 'auto',
//           overflowX: 'hidden',
//           scrollbarGutter: 'stable',
//           position: 'relative',
//         }}
//       >
//         {messages.length > 0 ? (
//           messages.map((msg, index) => (
//             <div
//               key={index}
//               className={`flex items-center ${
//                 msg.sender === "user" ? "justify-end" : "justify-start"
//               }`}
//               style={{
//                 width: "100%",
//               }}
//             >
//               {msg.sender === "bot" && (
//                 <img
//                   src={uniguru}
//                   alt="Bot Logo"
//                   className="w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 rounded-full mr-2 sm:mr-3 flex-shrink-0"
//                 />
//               )}
//               <div
//                 className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg relative ${
//                   msg.sender === "bot" && !msg.isLoading ? "flex flex-col" : "flex items-center"
//                 } ${
//                   msg.sender === "user"
//                     ? "bg-[linear-gradient(135deg,_#61ACEF,_#9987ED,_#B679E1,_#9791DB,_#74BDCC,_#59D2BF)] text-black"
//                     : "border border-gray-700 text-white"
//                 }`}
//                 style={{
//                   display: "inline-block",
//                   maxWidth: "85%", // Increased for mobile
//                   wordWrap: "break-word",
//                   overflowWrap: "break-word",
//                   wordBreak: "break-word",
//                   alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
//                   marginTop: "10px",
//                   fontSize: window.innerWidth < 640 ? "14px" : "16px", // Responsive font size
//                   marginBottom: msg.sender === "bot" && !msg.isLoading ? (window.innerWidth < 640 ? "8px" : "20px") : "0px",
//                 }}
//               >
//                 {msg.isLoading ? (
//                   <div className="flex items-center space-x-3">
//                     <LoadingSpinner size="small" variant="dots" />
//                     <span className="text-purple-300 text-sm">Guru is thinking...</span>
//                   </div>
//                 ) : (
//                   <div className={msg.sender === "bot" ? "w-full" : ""}>
//                     {msg.text}
//                   </div>
//                 )}
//                 {msg.sender === "bot" && !msg.isLoading && (
//                   <div className="mt-2 flex items-center justify-end space-x-2 sm:absolute sm:bottom-[-18px] sm:mt-0 sm:bottom-[-20px] sm:right-0 sm:space-x-1.5 sm:space-x-2">
//                     {/* Audio Controls */}
//                     {isPlaying && playingMessageIndex === index ? (
//                       <div className="flex items-center space-x-1">
//                         <FontAwesomeIcon
//                           icon={window.speechSynthesis?.paused ? faPlay : faPause}
//                           className="text-purple-400 hover:text-purple-300 cursor-pointer transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                           onClick={() => handleTextToSpeech(msg.text, index)}
//                           title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
//                         />
//                         <FontAwesomeIcon
//                           icon={faStop}
//                           className="text-red-400 hover:text-red-300 cursor-pointer transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                           onClick={handleStopAudio}
//                           title="Stop audio"
//                         />
//                       </div>
//                     ) : (
//                       <FontAwesomeIcon
//                         icon={faVolumeHigh}
//                         className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
//                         style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                         onClick={() => handleTextToSpeech(msg.text, index)}
//                         title="Read aloud"
//                       />
//                     )}
//                     <FontAwesomeIcon
//                       icon={faCopy}
//                       className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
//                       style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                       onClick={() => handleCopyMessage(msg.text)}
//                       title="Copy message"
//                     />
//                   </div>
//                 )}
//                 {/* Chunk count icon for bot messages with retrieved_chunks */}
//                 {msg.sender === "bot" && !msg.isLoading && (
//                   <>
//                     {/* DEBUG: Show retrieved_chunks visually for every bot message */}
//                     <div style={{ color: '#00bcd4', fontSize: '11px', margin: '2px 0' }}>
//                       <b>[DEBUG]</b> retrieved_chunks: {Array.isArray(msg.retrieved_chunks) ? msg.retrieved_chunks.length : 'none'}
//                       {Array.isArray(msg.retrieved_chunks) && msg.retrieved_chunks.length > 0 && (
//                         <pre style={{ whiteSpace: 'pre-wrap', background: '#e0f7fa', color: '#333', padding: 4, borderRadius: 4, marginTop: 2 }}>{JSON.stringify(msg.retrieved_chunks, null, 2)}</pre>
//                       )}
//                     </div>
//                   </>
//                 )}
//   {/* Chunk Sidebar */}
//   <ChunkSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} chunks={sidebarChunks} />
//               </div>
//               {msg.sender === "user" && (
//                 <img
//                   src={userimage}
//                   alt="User"
//                   className="w-6 h-6 sm:w-8 sm:h-8 rounded-full ml-2 sm:ml-3 flex-shrink-0"
//                 />
//               )}
//             </div>
//           ))
//         ) : (
//           <>
//             {!selectedGuru ? (
//               <div></div>
//             ) : (
//               <div className="text-center">
//                 <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-purple-500/30 to-blue-500/30 rounded-full flex items-center justify-center border border-purple-400/20">
//                   <img src={guruLogo} alt="Guru" className="w-8 h-8" />
//                 </div>
//                 <p className="text-gray-400 text-sm sm:text-base">Ready to chat with {selectedGuru.name}!</p>
//                 <p className="text-gray-500 text-xs sm:text-sm mt-2">Expert in: {selectedGuru.subject}</p>
//               </div>
//             )}
//           </>
//         )}
//         <div ref={messagesEndRef} />
//       </div>

//       {/* Fixed Input Area */}
//       {selectedGuru ? (
//         <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 bg-gradient-to-t from-black/20 to-transparent">
//           <div className="w-full max-w-6xl mx-auto px-4 sm:px-8">
//             <EnhancedChatInput
//               message={message}
//               setMessage={setMessage}
//               onSendMessage={handleSendMessage}
//               onKeyDown={handleKeyDown}
//               textareaRef={textareaRef}
//               onFileUpload={handleFileUpload}
//               attachments={attachments}
//               onRemoveAttachment={handleRemoveAttachment}
//             />
//           </div>

//           <div className="text-center text-gray-400 mt-2 text-[10px] xs:text-xs sm:text-sm px-4">
//             Guru can make mistakes. Check important info.
//           </div>
//         </div>
//       ) : (
//         <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 fixed inset-0 flex items-center justify-center pointer-events-none">
//           <div className="w-full max-w-3xl mx-auto px-4 sm:px-8 pointer-events-auto">
//             <div className="bg-gradient-to-br from-white/10 via-white/5 to-transparent backdrop-blur-xl rounded-3xl border border-white/20 p-12 sm:p-16 text-center shadow-2xl shadow-black/20 transform hover:scale-105 transition-all duration-300">
//               <div className="flex items-center justify-center gap-3 mb-6">
//                 <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-lg">
//                   <img src={guruLogo} alt="Guru" className="w-7 h-7" />
//                 </div>
//                 <h4 className="text-white font-semibold text-lg sm:text-xl bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">No guru selected</h4>
//               </div>
//               <p className="text-gray-300 text-sm sm:text-base mb-8 leading-relaxed">
//                 Create or select a guru to start chatting.
//               </p>
//               <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
//                 <button
//                   onClick={() => {
//                     window.dispatchEvent(new CustomEvent('open-guru-create'));
//                   }}
//                   className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-purple-600 via-purple-500 to-blue-600 hover:from-purple-500 hover:via-purple-400 hover:to-blue-500 text-white text-sm font-semibold shadow-xl shadow-purple-500/30 transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 border border-purple-400/30"
//                 >
//                   Create Guru
//                 </button>
//                 <button
//                   onClick={() => {
//                     window.dispatchEvent(new CustomEvent('restart-guru-onboarding'));
//                   }}
//                   className="w-full sm:w-auto px-8 py-3 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 hover:border-white/30 text-white text-sm font-semibold backdrop-blur-sm transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 shadow-lg"
//                 >
//                   How to Guru?
//                 </button>
//               </div>
//             </div>
//           </div>
//         </div>
//       )}


//     </div>
//   );
// };

// export default ChatContainer;




// import { useState, useRef, useEffect } from "react";
// import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
// import { faCopy, faVolumeHigh, faPause, faPlay, faStop, faDatabase } from "@fortawesome/free-solid-svg-icons";
// import uniguru from "../assets/uni-logo.png";
// import userimage from "../assets/userimage.png";
// import guruLogo from "../assets/guru.png";

// import EnhancedChatInput from "./EnhancedChatInput";
// import LoadingSpinner from "./LoadingSpinner";
// import ChunkSidebar from "./ChunkSidebar";
// import toast from "react-hot-toast";
// import { useAuth } from "../context/AuthContext";
// import { useChat } from "../context/ChatContext";
// import { useGuru } from "../context/GuruContext";
// import { sendChatRequest, getChatSessionById, scanImageText, readPdf } from "../helpers/api-communicator";

// interface Message {
//   text: string;
//   sender: "user" | "bot";
//   timestamp?: Date;
//   isLoading?: boolean;
//   retrieved_chunks?: Array<{ index: number; file: string; score: number; content: string }>;
// }

// interface FileAttachment {
//   id: string;
//   file: File;
//   type: 'image' | 'pdf' | 'document';
//   preview?: string;
// }

// const ChatContainer: React.FC = () => {
//   const { user } = useAuth();
//   const { currentChatId } = useChat();
//   const { selectedGuru } = useGuru();

//   const [messages, setMessages] = useState<Message[]>([]);
//   const [message, setMessage] = useState<string>("");
//   const [attachments, setAttachments] = useState<FileAttachment[]>([]);
//   const [isLoading, setIsLoading] = useState(false);
//   const [isPlaying, setIsPlaying] = useState(false);
//   const [, setCurrentUtterance] = useState<SpeechSynthesisUtterance | null>(null);
//   const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
//   // Sidebar state
//   const [sidebarOpen, setSidebarOpen] = useState(false);
//   const [sidebarChunks, setSidebarChunks] = useState<Array<{ index: number; file: string; score: number; content: string }>>([]);

//   const messagesEndRef = useRef<HTMLDivElement | null>(null);
//   const messagesContainerRef = useRef<HTMLDivElement | null>(null);
//   const textareaRef = useRef<HTMLTextAreaElement | null>(null);

//   const scrollToBottom = () => {
//     if (messagesEndRef.current) {
//       messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
//     }
//   };

//   // Always scroll to bottom for all messages (new and loaded)
//   useEffect(() => {
//     scrollToBottom();
//   }, [messages]);

//   // Cleanup audio on component unmount
//   useEffect(() => {
//     return () => {
//       if ('speechSynthesis' in window) {
//         window.speechSynthesis.cancel();
//       }
//     };
//   }, []);

//   // Keyboard shortcuts for audio control
//   useEffect(() => {
//     const handleKeyDown = (event: KeyboardEvent) => {
//       if (event.key === 'Escape' && isPlaying) {
//         handleStopAudio();
//       }
//     };

//     document.addEventListener('keydown', handleKeyDown);
//     return () => {
//       document.removeEventListener('keydown', handleKeyDown);
//     };
//   }, [isPlaying]);

//   // Clear messages when guru changes
//   useEffect(() => {
//     setMessages([]);
//     console.log(`Cleared messages due to guru change: ${selectedGuru?.name || 'None'}`);
//   }, [selectedGuru]);

//   // Load chat history when current chat changes
//   useEffect(() => {
//     const loadChatHistory = async () => {
//       if (currentChatId) {
//         try {
//           console.log(`Loading chat history for chat ID: ${currentChatId}`);
//           const response = await getChatSessionById(currentChatId);
//           const chatMessages = response.chat.messages || [];
//           const formattedMessages = chatMessages.map((msg: any) => ({
//             text: msg.content,
//             sender: msg.sender === 'user' ? 'user' : 'bot',
//             timestamp: new Date(msg.timestamp),
//             retrieved_chunks: msg.metadata && Array.isArray(msg.metadata.retrieved_chunks)
//               ? msg.metadata.retrieved_chunks.map((chunk: any) => ({
//                   index: chunk.index || 0,
//                   file: chunk.file || '',
//                   score: chunk.score || 0,
//                   content: chunk.content || ''
//                 }))
//               : []
//           }));
//           setMessages(formattedMessages);
//           console.log(`Loaded ${formattedMessages.length} messages for chat ${currentChatId}`);

//           if (formattedMessages.length > 0) {
//             toast.success(`Loaded ${formattedMessages.length} previous messages`, {
//               duration: 2000,
//               icon: '💬'
//             });
//           }
//         } catch (error) {
//           console.error('Error loading chat history:', error);
//           toast.error("Failed to load chat history", {
//             duration: 2000,
//             icon: '⚠️'
//           });
//           setMessages([]);
//         }
//       } else {
//         console.log('No current chat selected, clearing messages');
//         setMessages([]);
//       }
//     };

//     loadChatHistory();
//   }, [currentChatId]);

//   const handleSendMessage = async () => {
//     if ((!message.trim() && attachments.length === 0) || !selectedGuru || !user || isLoading) {
//       return;
//     }

//     const userMessage = message.trim();
//     setMessage("");
//     setIsLoading(true);

//     const attachmentContent = await processAttachments();
//     const fullMessage = userMessage + attachmentContent;

//     setAttachments([]);

//     const newUserMessage: Message = {
//       text: userMessage + (attachments.length > 0 ? ` [${attachments.length} file(s) attached]` : ''),
//       sender: "user",
//       timestamp: new Date()
//     };
//     setMessages(prev => [...prev, newUserMessage]);

//     const loadingMessage: Message = {
//       text: "Thinking...",
//       sender: "bot",
//       timestamp: new Date(),
//       isLoading: true
//     };
//     setMessages(prev => [...prev, loadingMessage]);

//     const textarea = document.querySelector("textarea");
//     if (textarea) {
//       textarea.style.height = "auto";
//     }

//     try {
//       const context = messages
//         .slice(-3)
//         .filter((msg) => !msg.isLoading)
//         .map((msg) => ({
//           sender: msg.sender,
//           content: msg.text,
//           timestamp: msg.timestamp ? new Date(msg.timestamp).toISOString() : new Date().toISOString(),
//         }));

//       const response = await sendChatRequest(
//         fullMessage,
//         selectedGuru.id,
//         user.id,
//         currentChatId || undefined,
//         context
//       );

//       console.log('[DEBUG] sendChatRequest response:', JSON.stringify(response, null, 2));

//       if (response.aiResponse) {
//         const botMessage: Message = {
//           text: response.aiResponse.content || 'No response content',
//           sender: "bot",
//           timestamp: new Date(),
//           retrieved_chunks: Array.isArray(response.aiResponse.metadata?.retrieved_chunks)
//             ? response.aiResponse.metadata.retrieved_chunks.map((chunk: any) => ({
//                 index: chunk.index || 0,
//                 file: chunk.file || '',
//                 score: chunk.score || 0,
//                 content: chunk.content || ''
//               }))
//             : []
//         };

//         console.log('[DEBUG] Bot message with chunks:', JSON.stringify(botMessage, null, 2));

//         setMessages(prev => {
//           const newMessages = [...prev];
//           newMessages.pop();
//           newMessages.push(botMessage);
//           console.log('[DEBUG] Updated messages state:', JSON.stringify(newMessages.slice(-2), null, 2));
//           return newMessages;
//         });

//         if (response.chat && response.chat.id && !currentChatId) {
//           console.log(`New chat created with ID: ${response.chat.id}`);
//         }
//       } else {
//         throw new Error('No aiResponse in response');
//       }
//     } catch (error) {
//       console.error('Error sending message:', error);
//       toast.error("Failed to send message. Please try again.", {
//         duration: 3000,
//         icon: '❌'
//       });

//       const errorMessage: Message = {
//         text: "Sorry, I'm having trouble responding right now. Please try again.",
//         sender: "bot",
//         timestamp: new Date(),
//         retrieved_chunks: []
//       };

//       setMessages(prev => {
//         const newMessages = [...prev];
//         newMessages.pop();
//         newMessages.push(errorMessage);
//         return newMessages;
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
//     if (e.key === "Enter" && !e.shiftKey) {
//       e.preventDefault();
//       handleSendMessage();
//     }
//   };

//   const handleCopyMessage = async (text: string) => {
//     try {
//       await navigator.clipboard.writeText(text);
//       toast.success("Message copied to clipboard!", {
//         duration: 2000,
//         icon: '📋'
//       });
//     } catch (err) {
//       console.error('Failed to copy text: ', err);
//       const textArea = document.createElement('textarea');
//       textArea.value = text;
//       document.body.appendChild(textArea);
//       textArea.select();
//       document.execCommand('copy');
//       document.body.removeChild(textArea);
//       toast.success("Message copied to clipboard!", {
//         duration: 2000,
//         icon: '📋'
//       });
//     }
//   };

//   const handleTextToSpeech = (text: string, messageIndex: number) => {
//     if ('speechSynthesis' in window) {
//       if (isPlaying && playingMessageIndex === messageIndex) {
//         if (window.speechSynthesis.paused) {
//           window.speechSynthesis.resume();
//           toast.success("Audio resumed", {
//             duration: 1000,
//             icon: '▶️'
//           });
//         } else {
//           window.speechSynthesis.pause();
//           toast.success("Audio paused", {
//             duration: 1000,
//             icon: '⏸️'
//           });
//         }
//         return;
//       }

//       window.speechSynthesis.cancel();
//       setIsPlaying(false);
//       setCurrentUtterance(null);
//       setPlayingMessageIndex(null);

//       const utterance = new SpeechSynthesisUtterance(text);
//       utterance.rate = 0.9;
//       utterance.pitch = 1;
//       utterance.volume = 0.8;

//       const voices = window.speechSynthesis.getVoices();
//       const preferredVoice = voices.find(voice =>
//         voice.name.includes('Google') ||
//         voice.name.includes('Microsoft') ||
//         voice.lang.startsWith('en')
//       );

//       if (preferredVoice) {
//         utterance.voice = preferredVoice;
//       }

//       utterance.onstart = () => {
//         setIsPlaying(true);
//         setCurrentUtterance(utterance);
//         setPlayingMessageIndex(messageIndex);
//         toast.success("Playing audio...", {
//           duration: 1500,
//           icon: '🔊'
//         });
//       };

//       utterance.onend = () => {
//         setIsPlaying(false);
//         setCurrentUtterance(null);
//         setPlayingMessageIndex(null);
//         toast.success("Audio finished", {
//           duration: 1000,
//           icon: '✅'
//         });
//       };

//       utterance.onerror = (_event) => {
//         setIsPlaying(false);
//         setCurrentUtterance(null);
//         setPlayingMessageIndex(null);
//         toast.error("Failed to play audio", {
//           duration: 2000,
//           icon: '❌'
//         });
//       };

//       window.speechSynthesis.speak(utterance);
//     } else {
//       toast.error("Text-to-speech not supported in this browser", {
//         duration: 3000,
//         icon: '❌'
//       });
//     }
//   };

//   const handleStopAudio = () => {
//     if ('speechSynthesis' in window) {
//       window.speechSynthesis.cancel();
//       setIsPlaying(false);
//       setCurrentUtterance(null);
//       setPlayingMessageIndex(null);
//       toast.success("Audio stopped", {
//         duration: 1000,
//         icon: '⏹️'
//       });
//     }
//   };

//   const handleFileUpload = async (file: File) => {
//     const fileType = file.type;
//     const fileName = file.name.toLowerCase();

//     let type: 'image' | 'pdf' | 'document' = 'document';
//     if (fileType.startsWith('image/')) {
//       type = 'image';
//     } else if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
//       type = 'pdf';
//     }

//     const attachment: FileAttachment = {
//       id: Date.now().toString(),
//       file,
//       type,
//     };

//     if (type === 'image') {
//       const reader = new FileReader();
//       reader.onload = (e) => {
//         attachment.preview = e.target?.result as string;
//         setAttachments(prev => [...prev, attachment]);
//       };
//       reader.readAsDataURL(file);
//     } else {
//       setAttachments(prev => [...prev, attachment]);
//     }

//     toast.success(`${type === 'image' ? 'Image' : type === 'pdf' ? 'PDF' : 'File'} attached successfully!`, {
//       duration: 2000,
//       icon: type === 'image' ? '🖼️' : type === 'pdf' ? '📄' : '📎'
//     });
//   };

//   const handleRemoveAttachment = (id: string) => {
//     setAttachments(prev => prev.filter(att => att.id !== id));
//     toast.success("File removed", {
//       duration: 1500,
//       icon: '🗑️'
//     });
//   };

//   const processAttachments = async (): Promise<string> => {
//     if (attachments.length === 0) return '';

//     let extractedContent = '';

//     for (const attachment of attachments) {
//       try {
//         if (attachment.type === 'image') {
//           toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
//           const result = await scanImageText(attachment.file);
//           if (result.extractedText) {
//             extractedContent += `\n\n[Image: ${attachment.file.name}]\n${result.extractedText}`;
//             toast.success(`Image processed successfully!`, { id: `process-${attachment.id}`, icon: '🖼️' });
//           }
//         } else if (attachment.type === 'pdf') {
//           toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
//           const result = await readPdf(attachment.file);
//           if (result.extractedText) {
//             extractedContent += `\n\n[PDF: ${attachment.file.name}]\n${result.extractedText}`;
//             toast.success(`PDF processed successfully!`, { id: `process-${attachment.id}`, icon: '📄' });
//           }
//         }
//       } catch (error) {
//         console.error(`Error processing ${attachment.file.name}:`, error);
//         toast.error(`Failed to process ${attachment.file.name}`, { id: `process-${attachment.id}` });
//       }
//     }

//     return extractedContent;
//   };

//   return (
//     <div
//       className="chat-container flex flex-col text-white transition-all duration-300 relative overflow-hidden"
//       style={{
//         width: "100%",
//       }}
//     >
//       {/* Selected Guru Display */}
//       {selectedGuru && (
//         <div className="w-full flex justify-center px-3 sm:px-4 pt-4 pb-3 flex-shrink-0">
//           <div className="max-w-md w-full bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10">
//             <div className="flex items-center justify-center gap-3">
//               <div className="relative">
//                 <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-purple-600 rounded-full flex items-center justify-center">
//                   <img src={guruLogo} alt="Guru" className="w-6 h-6" />
//                 </div>
//                 <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-900"></div>
//               </div>
//               <div className="text-center">
//                 <h3 className="text-white font-medium text-sm">
//                   {selectedGuru.name}
//                 </h3>
//                 <p className="text-gray-400 text-xs">
//                   {selectedGuru.subject}
//                 </p>
//               </div>
//               <div className="text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded-full">
//                 Active
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Audio Status Indicator */}
//       {isPlaying && (
//         <div className="w-full flex justify-center px-3 sm:px-4 pb-3 flex-shrink-0">
//           <div className="max-w-sm w-full bg-green-500/10 backdrop-blur-sm rounded-lg p-3 border border-green-400/20">
//             <div className="flex items-center justify-center gap-3">
//               <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
//               <span className="text-green-300 text-sm">Audio playing...</span>
//               <div className="flex items-center space-x-2">
//                 <FontAwesomeIcon
//                   icon={window.speechSynthesis?.paused ? faPlay : faPause}
//                   className="text-green-400 hover:text-green-300 cursor-pointer transition-colors text-sm"
//                   onClick={() => {
//                     if (playingMessageIndex !== null) {
//                       const message = messages[playingMessageIndex];
//                       if (message) {
//                         handleTextToSpeech(message.text, playingMessageIndex);
//                       }
//                     }
//                   }}
//                   title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
//                 />
//                 <FontAwesomeIcon
//                   icon={faStop}
//                   className="text-red-400 hover:text-red-300 cursor-pointer transition-colors text-sm"
//                   onClick={handleStopAudio}
//                   title="Stop audio"
//                 />
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Chat messages */}
//       <div
//         ref={messagesContainerRef}
//         className={`chat-messages-area flex-1 w-full max-w-6xl flex px-4 sm:px-8 py-2 chat-messages-container mx-auto ${
//           messages.length > 0 ? 'flex-col gap-3 sm:gap-4' : 'items-center justify-center lg:min-h-[60vh]'
//         }`}
//         style={{
//           minHeight: 0,
//           overflowY: 'auto',
//           overflowX: 'hidden',
//           scrollbarGutter: 'stable',
//           position: 'relative',
//         }}
//       >
//         {messages.length > 0 ? (
//           messages.map((msg, index) => (
//             <div
//               key={index}
//               className={`flex items-center ${
//                 msg.sender === "user" ? "justify-end" : "justify-start"
//               }`}
//               style={{
//                 width: "100%",
//               }}
//             >
//               {msg.sender === "bot" && (
//                 <img
//                   src={uniguru}
//                   alt="Bot Logo"
//                   className="w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 rounded-full mr-2 sm:mr-3 flex-shrink-0"
//                 />
//               )}
//               <div
//                 className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg relative ${
//                   msg.sender === "bot" && !msg.isLoading ? "flex flex-col" : "flex items-center"
//                 } ${
//                   msg.sender === "user"
//                     ? "bg-[linear-gradient(135deg,_#61ACEF,_#9987ED,_#B679E1,_#9791DB,_#74BDCC,_#59D2BF)] text-black"
//                     : "border border-gray-700 text-white"
//                 }`}
//                 style={{
//                   display: "inline-block",
//                   maxWidth: "85%",
//                   wordWrap: "break-word",
//                   overflowWrap: "break-word",
//                   wordBreak: "break-word",
//                   alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
//                   marginTop: "10px",
//                   fontSize: window.innerWidth < 640 ? "14px" : "16px",
//                   marginBottom: msg.sender === "bot" && !msg.isLoading ? (window.innerWidth < 640 ? "8px" : "20px") : "0px",
//                 }}
//               >
//                 {msg.isLoading ? (
//                   <div className="flex items-center space-x-3">
//                     <LoadingSpinner size="small" variant="dots" />
//                     <span className="text-purple-300 text-sm">Guru is thinking...</span>
//                   </div>
//                 ) : (
//                   <div className={msg.sender === "bot" ? "w-full" : ""}>
//                     {msg.text}
//                   </div>
//                 )}
//                 {msg.sender === "bot" && !msg.isLoading && (
//                   <div className="mt-2 flex items-center justify-end space-x-2 sm:absolute sm:bottom-[-18px] sm:mt-0 sm:bottom-[-20px] sm:right-0 sm:space-x-1.5 sm:space-x-2">
//                     {/* Audio Controls */}
//                     {isPlaying && playingMessageIndex === index ? (
//                       <div className="flex items-center space-x-1">
//                         <FontAwesomeIcon
//                           icon={window.speechSynthesis?.paused ? faPlay : faPause}
//                           className="text-purple-400 hover:text-purple-300 cursor-pointer transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                           onClick={() => handleTextToSpeech(msg.text, index)}
//                           title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
//                         />
//                         <FontAwesomeIcon
//                           icon={faStop}
//                           className="text-red-400 hover:text-red-300 cursor-pointer transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                           onClick={handleStopAudio}
//                           title="Stop audio"
//                         />
//                       </div>
//                     ) : (
//                       <FontAwesomeIcon
//                         icon={faVolumeHigh}
//                         className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
//                         style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                         onClick={() => handleTextToSpeech(msg.text, index)}
//                         title="Read aloud"
//                       />
//                     )}
//                     <FontAwesomeIcon
//                       icon={faCopy}
//                       className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
//                       style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                       onClick={() => handleCopyMessage(msg.text)}
//                       title="Copy message"
//                     />
//                     {/* Chunk count icon */}
//                     {Array.isArray(msg.retrieved_chunks) && msg.retrieved_chunks.length > 0 && (
//                       <div
//                         className="flex items-center space-x-1 cursor-pointer"
//                         onClick={() => {
//                           setSidebarChunks(msg.retrieved_chunks || []);
//                           setSidebarOpen(true);
//                         }}
//                         title={`View ${msg.retrieved_chunks.length} retrieved chunks`}
//                       >
//                         <FontAwesomeIcon
//                           icon={faDatabase}
//                           className="text-gray-400 hover:text-purple-400 transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                         />
//                         <span className="text-gray-400 text-xs">{msg.retrieved_chunks.length}</span>
//                       </div>
//                     )}
//                   </div>
//                 )}
//                 {/* DEBUG: Show retrieved_chunks visually for every bot message */}
//                 {msg.sender === "bot" && !msg.isLoading && (
//                   <div style={{ color: '#00bcd4', fontSize: '11px', margin: '2px 0' }}>
//                     <b>[DEBUG]</b> retrieved_chunks: {Array.isArray(msg.retrieved_chunks) ? msg.retrieved_chunks.length : 'none'}
//                     {Array.isArray(msg.retrieved_chunks) && msg.retrieved_chunks.length > 0 && (
//                       <pre style={{ whiteSpace: 'pre-wrap', background: '#e0f7fa', color: '#333', padding: 4, borderRadius: 4, marginTop: 2 }}>
//                         {JSON.stringify(msg.retrieved_chunks, null, 2)}
//                       </pre>
//                     )}
//                   </div>
//                 )}
//               </div>
//               {msg.sender === "user" && (
//                 <img
//                   src={userimage}
//                   alt="User"
//                   className="w-6 h-6 sm:w-8 sm:h-8 rounded-full ml-2 sm:ml-3 flex-shrink-0"
//                 />
//               )}
//             </div>
//           ))
//         ) : (
//           <>
//             {!selectedGuru ? (
//               <div></div>
//             ) : (
//               <div className="text-center">
//                 <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-purple-500/30 to-blue-500/30 rounded-full flex items-center justify-center border border-purple-400/20">
//                   <img src={guruLogo} alt="Guru" className="w-8 h-8" />
//                 </div>
//                 <p className="text-gray-400 text-sm sm:text-base">Ready to chat with {selectedGuru.name}!</p>
//                 <p className="text-gray-500 text-xs sm:text-sm mt-2">Expert in: {selectedGuru.subject}</p>
//               </div>
//             )}
//           </>
//         )}
//         <div ref={messagesEndRef} />
//         <ChunkSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} chunks={sidebarChunks} />
//       </div>

//       {/* Fixed Input Area */}
//       {selectedGuru ? (
//         <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 bg-gradient-to-t from-black/20 to-transparent">
//           <div className="w-full max-w-6xl mx-auto px-4 sm:px-8">
//             <EnhancedChatInput
//               message={message}
//               setMessage={setMessage}
//               onSendMessage={handleSendMessage}
//               onKeyDown={handleKeyDown}
//               textareaRef={textareaRef}
//               onFileUpload={handleFileUpload}
//               attachments={attachments}
//               onRemoveAttachment={handleRemoveAttachment}
//             />
//           </div>
//           <div className="text-center text-gray-400 mt-2 text-[10px] xs:text-xs sm:text-sm px-4">
//             Guru can make mistakes. Check important info.
//           </div>
//         </div>
//       ) : (
//         <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 fixed inset-0 flex items-center justify-center pointer-events-none">
//           <div className="w-full max-w-3xl mx-auto px-4 sm:px-8 pointer-events-auto">
//             <div className="bg-gradient-to-br from-white/10 via-white/5 to-transparent backdrop-blur-xl rounded-3xl border border-white/20 p-12 sm:p-16 text-center shadow-2xl shadow-black/20 transform hover:scale-105 transition-all duration-300">
//               <div className="flex items-center justify-center gap-3 mb-6">
//                 <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-lg">
//                   <img src={guruLogo} alt="Guru" className="w-7 h-7" />
//                 </div>
//                 <h4 className="text-white font-semibold text-lg sm:text-xl bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">No guru selected</h4>
//               </div>
//               <p className="text-gray-300 text-sm sm:text-base mb-8 leading-relaxed">
//                 Create or select a guru to start chatting.
//               </p>
//               <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
//                 <button
//                   onClick={() => {
//                     window.dispatchEvent(new CustomEvent('open-guru-create'));
//                   }}
//                   className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-purple-600 via-purple-500 to-blue-600 hover:from-purple-500 hover:via-purple-400 hover:to-blue-500 text-white text-sm font-semibold shadow-xl shadow-purple-500/30 transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 border border-purple-400/30"
//                 >
//                   Create Guru
//                 </button>
//                 <button
//                   onClick={() => {
//                     window.dispatchEvent(new CustomEvent('restart-guru-onboarding'));
//                   }}
//                   className="w-full sm:w-auto px-8 py-3 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 hover:border-white/30 text-white text-sm font-semibold backdrop-blur-sm transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 shadow-lg"
//                 >
//                   How to Guru?
//                 </button>
//               </div>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// };

// export default ChatContainer;


// import { useState, useRef, useEffect } from "react";
// import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
// import { faCopy, faVolumeHigh, faPause, faPlay, faStop, faSearch } from "@fortawesome/free-solid-svg-icons";
// import uniguru from "../assets/uni-logo.png";
// import userimage from "../assets/userimage.png";
// import guruLogo from "../assets/guru.png";

// import EnhancedChatInput from "./EnhancedChatInput";
// import LoadingSpinner from "./LoadingSpinner";
// import ChunkSidebar from "./ChunkSidebar";
// import toast from "react-hot-toast";
// import { useAuth } from "../context/AuthContext";
// import { useChat } from "../context/ChatContext";
// import { useGuru } from "../context/GuruContext";
// import { sendChatRequest, getChatSessionById, scanImageText, readPdf } from "../helpers/api-communicator";

// interface Message {
//   text: string;
//   sender: "user" | "bot";
//   timestamp?: Date;
//   isLoading?: boolean;
//   retrieved_chunks?: Array<{ index: number; file: string; score: number; content: string }>;
// }

// interface FileAttachment {
//   id: string;
//   file: File;
//   type: 'image' | 'pdf' | 'document';
//   preview?: string;
// }

// const ChatContainer: React.FC = () => {
//   const { user } = useAuth();
//   const { currentChatId } = useChat();
//   const { selectedGuru } = useGuru();

//   const [messages, setMessages] = useState<Message[]>([]);
//   const [message, setMessage] = useState<string>("");
//   const [attachments, setAttachments] = useState<FileAttachment[]>([]);
//   const [isLoading, setIsLoading] = useState(false);
//   const [isPlaying, setIsPlaying] = useState(false);
//   const [, setCurrentUtterance] = useState<SpeechSynthesisUtterance | null>(null);
//   const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
//   // Sidebar state
//   const [sidebarOpen, setSidebarOpen] = useState(false);
//   const [sidebarChunks, setSidebarChunks] = useState<Array<{ index: number; file: string; score: number; content: string }>>([]);

//   const messagesEndRef = useRef<HTMLDivElement | null>(null);
//   const messagesContainerRef = useRef<HTMLDivElement | null>(null);
//   const textareaRef = useRef<HTMLTextAreaElement | null>(null);

//   const scrollToBottom = () => {
//     if (messagesEndRef.current) {
//       messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
//     }
//   };

//   // Always scroll to bottom for all messages (new and loaded)
//   useEffect(() => {
//     scrollToBottom();
//   }, [messages]);

//   // Cleanup audio on component unmount
//   useEffect(() => {
//     return () => {
//       if ('speechSynthesis' in window) {
//         window.speechSynthesis.cancel();
//       }
//     };
//   }, []);

//   // Keyboard shortcuts for audio control
//   useEffect(() => {
//     const handleKeyDown = (event: KeyboardEvent) => {
//       if (event.key === 'Escape' && isPlaying) {
//         handleStopAudio();
//       }
//     };

//     document.addEventListener('keydown', handleKeyDown);
//     return () => {
//       document.removeEventListener('keydown', handleKeyDown);
//     };
//   }, [isPlaying]);

//   // Clear messages when guru changes
//   useEffect(() => {
//     setMessages([]);
//     console.log(`Cleared messages due to guru change: ${selectedGuru?.name || 'None'}`);
//   }, [selectedGuru]);

//   // Load chat history when current chat changes
//   useEffect(() => {
//     const loadChatHistory = async () => {
//       if (currentChatId) {
//         try {
//           console.log(`Loading chat history for chat ID: ${currentChatId}`);
//           const response = await getChatSessionById(currentChatId);
//           const chatMessages = response.chat.messages || [];
//           const formattedMessages = chatMessages.map((msg: any) => ({
//             text: msg.content,
//             sender: msg.sender === 'user' ? 'user' : 'bot',
//             timestamp: new Date(msg.timestamp),
//             retrieved_chunks: msg.metadata && Array.isArray(msg.metadata.retrieved_chunks)
//               ? msg.metadata.retrieved_chunks.map((chunk: any) => ({
//                   index: chunk.index || 0,
//                   file: chunk.file || '',
//                   score: chunk.score || 0,
//                   content: chunk.content || ''
//                 }))
//               : []
//           }));
//           setMessages(formattedMessages);
//           console.log(`Loaded ${formattedMessages.length} messages for chat ${currentChatId}`);

//           if (formattedMessages.length > 0) {
//             toast.success(`Loaded ${formattedMessages.length} previous messages`, {
//               duration: 2000,
//               icon: '💬'
//             });
//           }
//         } catch (error) {
//           console.error('Error loading chat history:', error);
//           toast.error("Failed to load chat history", {
//             duration: 2000,
//             icon: '⚠️'
//           });
//           setMessages([]);
//         }
//       } else {
//         console.log('No current chat selected, clearing messages');
//         setMessages([]);
//       }
//     };

//     loadChatHistory();
//   }, [currentChatId]);

//   const handleSendMessage = async () => {
//     if ((!message.trim() && attachments.length === 0) || !selectedGuru || !user || isLoading) {
//       return;
//     }

//     const userMessage = message.trim();
//     setMessage("");
//     setIsLoading(true);

//     const attachmentContent = await processAttachments();
//     const fullMessage = userMessage + attachmentContent;

//     setAttachments([]);

//     const newUserMessage: Message = {
//       text: userMessage + (attachments.length > 0 ? ` [${attachments.length} file(s) attached]` : ''),
//       sender: "user",
//       timestamp: new Date()
//     };
//     setMessages(prev => [...prev, newUserMessage]);

//     const loadingMessage: Message = {
//       text: "Thinking...",
//       sender: "bot",
//       timestamp: new Date(),
//       isLoading: true
//     };
//     setMessages(prev => [...prev, loadingMessage]);

//     const textarea = document.querySelector("textarea");
//     if (textarea) {
//       textarea.style.height = "auto";
//     }

//     try {
//       const context = messages
//         .slice(-3)
//         .filter((msg) => !msg.isLoading)
//         .map((msg) => ({
//           sender: msg.sender,
//           content: msg.text,
//           timestamp: msg.timestamp ? new Date(msg.timestamp).toISOString() : new Date().toISOString(),
//         }));

//       const response = await sendChatRequest(
//         fullMessage,
//         selectedGuru.id,
//         user.id,
//         currentChatId || undefined,
//         context
//       );

//       console.log('[DEBUG] sendChatRequest response:', JSON.stringify(response, null, 2));

//       if (response.aiResponse) {
//         const botMessage: Message = {
//           text: response.aiResponse.content || 'No response content',
//           sender: "bot",
//           timestamp: new Date(),
//           retrieved_chunks: Array.isArray(response.aiResponse.metadata?.retrieved_chunks)
//             ? response.aiResponse.metadata.retrieved_chunks.map((chunk: any) => ({
//                 index: chunk.index || 0,
//                 file: chunk.file || '',
//                 score: chunk.score || 0,
//                 content: chunk.content || ''
//               }))
//             : []
//         };

//         console.log('[DEBUG] Bot message with chunks:', JSON.stringify(botMessage, null, 2));

//         setMessages(prev => {
//           const newMessages = [...prev];
//           newMessages.pop();
//           newMessages.push(botMessage);
//           console.log('[DEBUG] Updated messages state:', JSON.stringify(newMessages.slice(-2), null, 2));
//           return newMessages;
//         });

//         if (response.chat && response.chat.id && !currentChatId) {
//           console.log(`New chat created with ID: ${response.chat.id}`);
//         }
//       } else {
//         throw new Error('No aiResponse in response');
//       }
//     } catch (error) {
//       console.error('Error sending message:', error);
//       toast.error("Failed to send message. Please try again.", {
//         duration: 3000,
//         icon: '❌'
//       });

//       const errorMessage: Message = {
//         text: "Sorry, I'm having trouble responding right now. Please try again.",
//         sender: "bot",
//         timestamp: new Date(),
//         retrieved_chunks: []
//       };

//       setMessages(prev => {
//         const newMessages = [...prev];
//         newMessages.pop();
//         newMessages.push(errorMessage);
//         return newMessages;
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
//     if (e.key === "Enter" && !e.shiftKey) {
//       e.preventDefault();
//       handleSendMessage();
//     }
//   };

//   const handleCopyMessage = async (text: string) => {
//     try {
//       await navigator.clipboard.writeText(text);
//       toast.success("Message copied to clipboard!", {
//         duration: 2000,
//         icon: '📋'
//       });
//     } catch (err) {
//       console.error('Failed to copy text: ', err);
//       const textArea = document.createElement('textarea');
//       textArea.value = text;
//       document.body.appendChild(textArea);
//       textArea.select();
//       document.execCommand('copy');
//       document.body.removeChild(textArea);
//       toast.success("Message copied to clipboard!", {
//         duration: 2000,
//         icon: '📋'
//       });
//     }
//   };

//   const handleTextToSpeech = (text: string, messageIndex: number) => {
//     if ('speechSynthesis' in window) {
//       if (isPlaying && playingMessageIndex === messageIndex) {
//         if (window.speechSynthesis.paused) {
//           window.speechSynthesis.resume();
//           toast.success("Audio resumed", {
//             duration: 1000,
//             icon: '▶️'
//           });
//         } else {
//           window.speechSynthesis.pause();
//           toast.success("Audio paused", {
//             duration: 1000,
//             icon: '⏸️'
//           });
//         }
//         return;
//       }

//       window.speechSynthesis.cancel();
//       setIsPlaying(false);
//       setCurrentUtterance(null);
//       setPlayingMessageIndex(null);

//       const utterance = new SpeechSynthesisUtterance(text);
//       utterance.rate = 0.9;
//       utterance.pitch = 1;
//       utterance.volume = 0.8;

//       const voices = window.speechSynthesis.getVoices();
//       const preferredVoice = voices.find(voice =>
//         voice.name.includes('Google') ||
//         voice.name.includes('Microsoft') ||
//         voice.lang.startsWith('en')
//       );

//       if (preferredVoice) {
//         utterance.voice = preferredVoice;
//       }

//       utterance.onstart = () => {
//         setIsPlaying(true);
//         setCurrentUtterance(utterance);
//         setPlayingMessageIndex(messageIndex);
//         toast.success("Playing audio...", {
//           duration: 1500,
//           icon: '🔊'
//         });
//       };

//       utterance.onend = () => {
//         setIsPlaying(false);
//         setCurrentUtterance(null);
//         setPlayingMessageIndex(null);
//         toast.success("Audio finished", {
//           duration: 1000,
//           icon: '✅'
//         });
//       };

//       utterance.onerror = (_event) => {
//         setIsPlaying(false);
//         setCurrentUtterance(null);
//         setPlayingMessageIndex(null);
//         toast.error("Failed to play audio", {
//           duration: 2000,
//           icon: '❌'
//         });
//       };

//       window.speechSynthesis.speak(utterance);
//     } else {
//       toast.error("Text-to-speech not supported in this browser", {
//         duration: 3000,
//         icon: '❌'
//       });
//     }
//   };

//   const handleStopAudio = () => {
//     if ('speechSynthesis' in window) {
//       window.speechSynthesis.cancel();
//       setIsPlaying(false);
//       setCurrentUtterance(null);
//       setPlayingMessageIndex(null);
//       toast.success("Audio stopped", {
//         duration: 1000,
//         icon: '⏹️'
//       });
//     }
//   };

//   const handleFileUpload = async (file: File) => {
//     const fileType = file.type;
//     const fileName = file.name.toLowerCase();

//     let type: 'image' | 'pdf' | 'document' = 'document';
//     if (fileType.startsWith('image/')) {
//       type = 'image';
//     } else if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
//       type = 'pdf';
//     }

//     const attachment: FileAttachment = {
//       id: Date.now().toString(),
//       file,
//       type,
//     };

//     if (type === 'image') {
//       const reader = new FileReader();
//       reader.onload = (e) => {
//         attachment.preview = e.target?.result as string;
//         setAttachments(prev => [...prev, attachment]);
//       };
//       reader.readAsDataURL(file);
//     } else {
//       setAttachments(prev => [...prev, attachment]);
//     }

//     toast.success(`${type === 'image' ? 'Image' : type === 'pdf' ? 'PDF' : 'File'} attached successfully!`, {
//       duration: 2000,
//       icon: type === 'image' ? '🖼️' : type === 'pdf' ? '📄' : '📎'
//     });
//   };

//   const handleRemoveAttachment = (id: string) => {
//     setAttachments(prev => prev.filter(att => att.id !== id));
//     toast.success("File removed", {
//       duration: 1500,
//       icon: '🗑️'
//     });
//   };

//   const processAttachments = async (): Promise<string> => {
//     if (attachments.length === 0) return '';

//     let extractedContent = '';

//     for (const attachment of attachments) {
//       try {
//         if (attachment.type === 'image') {
//           toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
//           const result = await scanImageText(attachment.file);
//           if (result.extractedText) {
//             extractedContent += `\n\n[Image: ${attachment.file.name}]\n${result.extractedText}`;
//             toast.success(`Image processed successfully!`, { id: `process-${attachment.id}`, icon: '🖼️' });
//           }
//         } else if (attachment.type === 'pdf') {
//           toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
//           const result = await readPdf(attachment.file);
//           if (result.extractedText) {
//             extractedContent += `\n\n[PDF: ${attachment.file.name}]\n${result.extractedText}`;
//             toast.success(`PDF processed successfully!`, { id: `process-${attachment.id}`, icon: '📄' });
//           }
//         }
//       } catch (error) {
//         console.error(`Error processing ${attachment.file.name}:`, error);
//         toast.error(`Failed to process ${attachment.file.name}`, { id: `process-${attachment.id}` });
//       }
//     }

//     return extractedContent;
//   };

//   return (
//     <div
//       className="chat-container flex flex-col text-white transition-all duration-300 relative overflow-hidden"
//       style={{
//         width: "100%",
//       }}
//     >
//       {/* Selected Guru Display */}
//       {selectedGuru && (
//         <div className="w-full flex justify-center px-3 sm:px-4 pt-4 pb-3 flex-shrink-0">
//           <div className="max-w-md w-full bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10">
//             <div className="flex items-center justify-center gap-3">
//               <div className="relative">
//                 <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-purple-600 rounded-full flex items-center justify-center">
//                   <img src={guruLogo} alt="Guru" className="w-6 h-6" />
//                 </div>
//                 <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-900"></div>
//               </div>
//               <div className="text-center">
//                 <h3 className="text-white font-medium text-sm">
//                   {selectedGuru.name}
//                 </h3>
//                 <p className="text-gray-400 text-xs">
//                   {selectedGuru.subject}
//                 </p>
//               </div>
//               <div className="text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded-full">
//                 Active
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Audio Status Indicator */}
//       {isPlaying && (
//         <div className="w-full flex justify-center px-3 sm:px-4 pb-3 flex-shrink-0">
//           <div className="max-w-sm w-full bg-green-500/10 backdrop-blur-sm rounded-lg p-3 border border-green-400/20">
//             <div className="flex items-center justify-center gap-3">
//               <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
//               <span className="text-green-300 text-sm">Audio playing...</span>
//               <div className="flex items-center space-x-2">
//                 <FontAwesomeIcon
//                   icon={window.speechSynthesis?.paused ? faPlay : faPause}
//                   className="text-green-400 hover:text-green-300 cursor-pointer transition-colors text-sm"
//                   onClick={() => {
//                     if (playingMessageIndex !== null) {
//                       const message = messages[playingMessageIndex];
//                       if (message) {
//                         handleTextToSpeech(message.text, playingMessageIndex);
//                       }
//                     }
//                   }}
//                   title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
//                 />
//                 <FontAwesomeIcon
//                   icon={faStop}
//                   className="text-red-400 hover:text-red-300 cursor-pointer transition-colors text-sm"
//                   onClick={handleStopAudio}
//                   title="Stop audio"
//                 />
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Chat messages */}
//       <div
//         ref={messagesContainerRef}
//         className={`chat-messages-area flex-1 w-full max-w-6xl flex px-4 sm:px-8 py-2 chat-messages-container mx-auto ${
//           messages.length > 0 ? 'flex-col gap-3 sm:gap-4' : 'items-center justify-center lg:min-h-[60vh]'
//         }`}
//         style={{
//           minHeight: 0,
//           overflowY: 'auto',
//           overflowX: 'hidden',
//           scrollbarGutter: 'stable',
//           position: 'relative',
//         }}
//       >
//         {messages.length > 0 ? (
//           messages.map((msg, index) => (
//             <div
//               key={index}
//               className={`flex items-center ${
//                 msg.sender === "user" ? "justify-end" : "justify-start"
//               }`}
//               style={{
//                 width: "100%",
//               }}
//             >
//               {msg.sender === "bot" && (
//                 <img
//                   src={uniguru}
//                   alt="Bot Logo"
//                   className="w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 rounded-full mr-2 sm:mr-3 flex-shrink-0"
//                 />
//               )}
//               <div
//                 className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg relative ${
//                   msg.sender === "bot" && !msg.isLoading ? "flex flex-col" : "flex items-center"
//                 } ${
//                   msg.sender === "user"
//                     ? "bg-[linear-gradient(135deg,_#61ACEF,_#9987ED,_#B679E1,_#9791DB,_#74BDCC,_#59D2BF)] text-black"
//                     : "border border-gray-700 text-white"
//                 }`}
//                 style={{
//                   display: "inline-block",
//                   maxWidth: "85%",
//                   wordWrap: "break-word",
//                   overflowWrap: "break-word",
//                   wordBreak: "break-word",
//                   alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
//                   marginTop: "10px",
//                   fontSize: window.innerWidth < 640 ? "14px" : "16px",
//                   marginBottom: msg.sender === "bot" && !msg.isLoading ? (window.innerWidth < 640 ? "8px" : "20px") : "0px",
//                 }}
//               >
//                 {msg.isLoading ? (
//                   <div className="flex items-center space-x-3">
//                     <LoadingSpinner size="small" variant="dots" />
//                     <span className="text-purple-300 text-sm">Guru is thinking...</span>
//                   </div>
//                 ) : (
//                   <div className={msg.sender === "bot" ? "w-full" : ""}>
//                     {msg.text}
//                   </div>
//                 )}
//                 {msg.sender === "bot" && !msg.isLoading && (
//                   <div className="mt-2 flex items-center justify-end space-x-2 sm:absolute sm:bottom-[-18px] sm:mt-0 sm:bottom-[-20px] sm:right-0 sm:space-x-1.5 sm:space-x-2">
//                     {/* Audio Controls */}
//                     {isPlaying && playingMessageIndex === index ? (
//                       <div className="flex items-center space-x-1">
//                         <FontAwesomeIcon
//                           icon={window.speechSynthesis?.paused ? faPlay : faPause}
//                           className="text-purple-400 hover:text-purple-300 cursor-pointer transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                           onClick={() => handleTextToSpeech(msg.text, index)}
//                           title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
//                         />
//                         <FontAwesomeIcon
//                           icon={faStop}
//                           className="text-red-400 hover:text-red-300 cursor-pointer transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                           onClick={handleStopAudio}
//                           title="Stop audio"
//                         />
//                       </div>
//                     ) : (
//                       <FontAwesomeIcon
//                         icon={faVolumeHigh}
//                         className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
//                         style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                         onClick={() => handleTextToSpeech(msg.text, index)}
//                         title="Read aloud"
//                       />
//                     )}
//                     <FontAwesomeIcon
//                       icon={faCopy}
//                       className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
//                       style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                       onClick={() => handleCopyMessage(msg.text)}
//                       title="Copy message"
//                     />
//                     {/* Search chunks icon */}
//                     {Array.isArray(msg.retrieved_chunks) && msg.retrieved_chunks.length > 0 && (
//                       <div
//                         className="flex items-center space-x-1 cursor-pointer"
//                         onClick={() => {
//                           setSidebarChunks(msg.retrieved_chunks || []);
//                           setSidebarOpen(true);
//                         }}
//                         title={`View ${msg.retrieved_chunks.length} searched chunks`}
//                       >
//                         <FontAwesomeIcon
//                           icon={faSearch}
//                           className="text-gray-400 hover:text-purple-400 transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                         />
//                         <span className="text-gray-400 text-xs">{msg.retrieved_chunks.length}</span>
//                       </div>
//                     )}
//                   </div>
//                 )}
//               </div>
//               {msg.sender === "user" && (
//                 <img
//                   src={userimage}
//                   alt="User"
//                   className="w-6 h-6 sm:w-8 sm:h-8 rounded-full ml-2 sm:ml-3 flex-shrink-0"
//                 />
//               )}
//             </div>
//           ))
//         ) : (
//           <>
//             {!selectedGuru ? (
//               <div></div>
//             ) : (
//               <div className="text-center">
//                 <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-purple-500/30 to-blue-500/30 rounded-full flex items-center justify-center border border-purple-400/20">
//                   <img src={guruLogo} alt="Guru" className="w-8 h-8" />
//                 </div>
//                 <p className="text-gray-400 text-sm sm:text-base">Ready to chat with {selectedGuru.name}!</p>
//                 <p className="text-gray-500 text-xs sm:text-sm mt-2">Expert in: {selectedGuru.subject}</p>
//               </div>
//             )}
//           </>
//         )}
//         <div ref={messagesEndRef} />
//         <ChunkSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} chunks={sidebarChunks} />
//       </div>

//       {/* Fixed Input Area */}
//       {selectedGuru ? (
//         <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 bg-gradient-to-t from-black/20 to-transparent">
//           <div className="w-full max-w-6xl mx-auto px-4 sm:px-8">
//             <EnhancedChatInput
//               message={message}
//               setMessage={setMessage}
//               onSendMessage={handleSendMessage}
//               onKeyDown={handleKeyDown}
//               textareaRef={textareaRef}
//               onFileUpload={handleFileUpload}
//               attachments={attachments}
//               onRemoveAttachment={handleRemoveAttachment}
//             />
//           </div>
//           <div className="text-center text-gray-400 mt-2 text-[10px] xs:text-xs sm:text-sm px-4">
//             Guru can make mistakes. Check important info.
//           </div>
//         </div>
//       ) : (
//         <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 fixed inset-0 flex items-center justify-center pointer-events-none">
//           <div className="w-full max-w-3xl mx-auto px-4 sm:px-8 pointer-events-auto">
//             <div className="bg-gradient-to-br from-white/10 via-white/5 to-transparent backdrop-blur-xl rounded-3xl border border-white/20 p-12 sm:p-16 text-center shadow-2xl shadow-black/20 transform hover:scale-105 transition-all duration-300">
//               <div className="flex items-center justify-center gap-3 mb-6">
//                 <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-lg">
//                   <img src={guruLogo} alt="Guru" className="w-7 h-7" />
//                 </div>
//                 <h4 className="text-white font-semibold text-lg sm:text-xl bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">No guru selected</h4>
//               </div>
//               <p className="text-gray-300 text-sm sm:text-base mb-8 leading-relaxed">
//                 Create or select a guru to start chatting.
//               </p>
//               <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
//                 <button
//                   onClick={() => {
//                     window.dispatchEvent(new CustomEvent('open-guru-create'));
//                   }}
//                   className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-purple-600 via-purple-500 to-blue-600 hover:from-purple-500 hover:via-purple-400 hover:to-blue-500 text-white text-sm font-semibold shadow-xl shadow-purple-500/30 transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 border border-purple-400/30"
//                 >
//                   Create Guru
//                 </button>
//                 <button
//                   onClick={() => {
//                     window.dispatchEvent(new CustomEvent('restart-guru-onboarding'));
//                   }}
//                   className="w-full sm:w-auto px-8 py-3 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 hover:border-white/30 text-white text-sm font-semibold backdrop-blur-sm transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 shadow-lg"
//                 >
//                   How to Guru?
//                 </button>
//               </div>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// };

// export default ChatContainer;


// import { useState, useRef, useEffect } from "react";
// import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
// import { faCopy, faVolumeHigh, faPause, faPlay, faStop, faMagnifyingGlassChart } from "@fortawesome/free-solid-svg-icons";
// import uniguru from "../assets/uni-logo.png";
// import userimage from "../assets/userimage.png";
// import guruLogo from "../assets/guru.png";

// import EnhancedChatInput from "./EnhancedChatInput";
// import LoadingSpinner from "./LoadingSpinner";
// import ChunkSidebar from "./ChunkSidebar";
// import toast from "react-hot-toast";
// import { useAuth } from "../context/AuthContext";
// import { useChat } from "../context/ChatContext";
// import { useGuru } from "../context/GuruContext";
// import { sendChatRequest, getChatSessionById, scanImageText, readPdf } from "../helpers/api-communicator";

// interface Message {
//   text: string;
//   sender: "user" | "bot";
//   timestamp?: Date;
//   isLoading?: boolean;
//   retrieved_chunks?: Array<{ index: number; file: string; score: number; content: string }>;
// }

// interface FileAttachment {
//   id: string;
//   file: File;
//   type: 'image' | 'pdf' | 'document';
//   preview?: string;
// }

// const ChatContainer: React.FC = () => {
//   const { user } = useAuth();
//   const { currentChatId } = useChat();
//   const { selectedGuru } = useGuru();

//   const [messages, setMessages] = useState<Message[]>([]);
//   const [message, setMessage] = useState<string>("");
//   const [attachments, setAttachments] = useState<FileAttachment[]>([]);
//   const [isLoading, setIsLoading] = useState(false);
//   const [isPlaying, setIsPlaying] = useState(false);
//   const [, setCurrentUtterance] = useState<SpeechSynthesisUtterance | null>(null);
//   const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
//   // Sidebar state
//   const [sidebarOpen, setSidebarOpen] = useState(false);
//   const [sidebarChunks, setSidebarChunks] = useState<Array<{ index: number; file: string; score: number; content: string }>>([]);
//   const [selectedChunk, setSelectedChunk] = useState<{ index: number; file: string; score: number; content: string } | null>(null);

//   const messagesEndRef = useRef<HTMLDivElement | null>(null);
//   const messagesContainerRef = useRef<HTMLDivElement | null>(null);
//   const textareaRef = useRef<HTMLTextAreaElement | null>(null);

//   const scrollToBottom = () => {
//     if (messagesEndRef.current) {
//       messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
//     }
//   };

//   // Always scroll to bottom for all messages (new and loaded)
//   useEffect(() => {
//     scrollToBottom();
//   }, [messages]);

//   // Cleanup audio on component unmount
//   useEffect(() => {
//     return () => {
//       if ('speechSynthesis' in window) {
//         window.speechSynthesis.cancel();
//       }
//     };
//   }, []);

//   // Keyboard shortcuts for audio control
//   useEffect(() => {
//     const handleKeyDown = (event: KeyboardEvent) => {
//       if (event.key === 'Escape' && isPlaying) {
//         handleStopAudio();
//       }
//     };

//     document.addEventListener('keydown', handleKeyDown);
//     return () => {
//       document.removeEventListener('keydown', handleKeyDown);
//     };
//   }, [isPlaying]);

//   // Clear messages when guru changes
//   useEffect(() => {
//     setMessages([]);
//     console.log(`Cleared messages due to guru change: ${selectedGuru?.name || 'None'}`);
//   }, [selectedGuru]);

//   // Load chat history when current chat changes
//   useEffect(() => {
//     const loadChatHistory = async () => {
//       if (currentChatId) {
//         try {
//           console.log(`Loading chat history for chat ID: ${currentChatId}`);
//           const response = await getChatSessionById(currentChatId);
//           const chatMessages = response.chat.messages || [];
//           const formattedMessages = chatMessages.map((msg: any) => ({
//             text: msg.content,
//             sender: msg.sender === 'user' ? 'user' : 'bot',
//             timestamp: new Date(msg.timestamp),
//             retrieved_chunks: msg.metadata && Array.isArray(msg.metadata.retrieved_chunks)
//               ? msg.metadata.retrieved_chunks.map((chunk: any) => ({
//                   index: chunk.index || 0,
//                   file: chunk.file || '',
//                   score: chunk.score || 0,
//                   content: chunk.content || ''
//                 }))
//               : []
//           }));
//           setMessages(formattedMessages);
//           console.log(`Loaded ${formattedMessages.length} messages for chat ${currentChatId}`);

//           if (formattedMessages.length > 0) {
//             toast.success(`Loaded ${formattedMessages.length} previous messages`, {
//               duration: 2000,
//               icon: '💬'
//             });
//           }
//         } catch (error) {
//           console.error('Error loading chat history:', error);
//           toast.error("Failed to load chat history", {
//             duration: 2000,
//             icon: '⚠️'
//           });
//           setMessages([]);
//         }
//       } else {
//         console.log('No current chat selected, clearing messages');
//         setMessages([]);
//       }
//     };

//     loadChatHistory();
//   }, [currentChatId]);

//   const handleSendMessage = async () => {
//     if ((!message.trim() && attachments.length === 0) || !selectedGuru || !user || isLoading) {
//       return;
//     }

//     const userMessage = message.trim();
//     setMessage("");
//     setIsLoading(true);

//     const attachmentContent = await processAttachments();
//     const fullMessage = userMessage + attachmentContent;

//     setAttachments([]);

//     const newUserMessage: Message = {
//       text: userMessage + (attachments.length > 0 ? ` [${attachments.length} file(s) attached]` : ''),
//       sender: "user",
//       timestamp: new Date()
//     };
//     setMessages(prev => [...prev, newUserMessage]);

//     const loadingMessage: Message = {
//       text: "Thinking...",
//       sender: "bot",
//       timestamp: new Date(),
//       isLoading: true
//     };
//     setMessages(prev => [...prev, loadingMessage]);

//     const textarea = document.querySelector("textarea");
//     if (textarea) {
//       textarea.style.height = "auto";
//     }

//     try {
//       const context = messages
//         .slice(-3)
//         .filter((msg) => !msg.isLoading)
//         .map((msg) => ({
//           sender: msg.sender,
//           content: msg.text,
//           timestamp: msg.timestamp ? new Date(msg.timestamp).toISOString() : new Date().toISOString(),
//         }));

//       const response = await sendChatRequest(
//         fullMessage,
//         selectedGuru.id,
//         user.id,
//         currentChatId || undefined,
//         context
//       );

//       console.log('[DEBUG] sendChatRequest response:', JSON.stringify(response, null, 2));

//       if (response.aiResponse) {
//         const botMessage: Message = {
//           text: response.aiResponse.content || 'No response content',
//           sender: "bot",
//           timestamp: new Date(),
//           retrieved_chunks: Array.isArray(response.aiResponse.metadata?.retrieved_chunks)
//             ? response.aiResponse.metadata.retrieved_chunks.map((chunk: any) => ({
//                 index: chunk.index || 0,
//                 file: chunk.file || '',
//                 score: chunk.score || 0,
//                 content: chunk.content || ''
//               }))
//             : []
//         };

//         console.log('[DEBUG] Bot message with chunks:', JSON.stringify(botMessage, null, 2));

//         setMessages(prev => {
//           const newMessages = [...prev];
//           newMessages.pop();
//           newMessages.push(botMessage);
//           console.log('[DEBUG] Updated messages state:', JSON.stringify(newMessages.slice(-2), null, 2));
//           return newMessages;
//         });

//         if (response.chat && response.chat.id && !currentChatId) {
//           console.log(`New chat created with ID: ${response.chat.id}`);
//         }
//       } else {
//         throw new Error('No aiResponse in response');
//       }
//     } catch (error) {
//       console.error('Error sending message:', error);
//       toast.error("Failed to send message. Please try again.", {
//         duration: 3000,
//         icon: '❌'
//       });

//       const errorMessage: Message = {
//         text: "Sorry, I'm having trouble responding right now. Please try again.",
//         sender: "bot",
//         timestamp: new Date(),
//         retrieved_chunks: []
//       };

//       setMessages(prev => {
//         const newMessages = [...prev];
//         newMessages.pop();
//         newMessages.push(errorMessage);
//         return newMessages;
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
//     if (e.key === "Enter" && !e.shiftKey) {
//       e.preventDefault();
//       handleSendMessage();
//     }
//   };

//   const handleCopyMessage = async (text: string) => {
//     try {
//       await navigator.clipboard.writeText(text);
//       toast.success("Message copied to clipboard!", {
//         duration: 2000,
//         icon: '📋'
//       });
//     } catch (err) {
//       console.error('Failed to copy text: ', err);
//       const textArea = document.createElement('textarea');
//       textArea.value = text;
//       document.body.appendChild(textArea);
//       textArea.select();
//       document.execCommand('copy');
//       document.body.removeChild(textArea);
//       toast.success("Message copied to clipboard!", {
//         duration: 2000,
//         icon: '📋'
//       });
//     }
//   };

//   const handleTextToSpeech = (text: string, messageIndex: number) => {
//     if ('speechSynthesis' in window) {
//       if (isPlaying && playingMessageIndex === messageIndex) {
//         if (window.speechSynthesis.paused) {
//           window.speechSynthesis.resume();
//           toast.success("Audio resumed", {
//             duration: 1000,
//             icon: '▶️'
//           });
//         } else {
//           window.speechSynthesis.pause();
//           toast.success("Audio paused", {
//             duration: 1000,
//             icon: '⏸️'
//           });
//         }
//         return;
//       }

//       window.speechSynthesis.cancel();
//       setIsPlaying(false);
//       setCurrentUtterance(null);
//       setPlayingMessageIndex(null);

//       const utterance = new SpeechSynthesisUtterance(text);
//       utterance.rate = 0.9;
//       utterance.pitch = 1;
//       utterance.volume = 0.8;

//       const voices = window.speechSynthesis.getVoices();
//       const preferredVoice = voices.find(voice =>
//         voice.name.includes('Google') ||
//         voice.name.includes('Microsoft') ||
//         voice.lang.startsWith('en')
//       );

//       if (preferredVoice) {
//         utterance.voice = preferredVoice;
//       }

//       utterance.onstart = () => {
//         setIsPlaying(true);
//         setCurrentUtterance(utterance);
//         setPlayingMessageIndex(messageIndex);
//         toast.success("Playing audio...", {
//           duration: 1500,
//           icon: '🔊'
//         });
//       };

//       utterance.onend = () => {
//         setIsPlaying(false);
//         setCurrentUtterance(null);
//         setPlayingMessageIndex(null);
//         toast.success("Audio finished", {
//           duration: 1000,
//           icon: '✅'
//         });
//       };

//       utterance.onerror = (_event) => {
//         setIsPlaying(false);
//         setCurrentUtterance(null);
//         setPlayingMessageIndex(null);
//         toast.error("Failed to play audio", {
//           duration: 2000,
//           icon: '❌'
//         });
//       };

//       window.speechSynthesis.speak(utterance);
//     } else {
//       toast.error("Text-to-speech not supported in this browser", {
//         duration: 3000,
//         icon: '❌'
//       });
//     }
//   };

//   const handleStopAudio = () => {
//     if ('speechSynthesis' in window) {
//       window.speechSynthesis.cancel();
//       setIsPlaying(false);
//       setCurrentUtterance(null);
//       setPlayingMessageIndex(null);
//       toast.success("Audio stopped", {
//         duration: 1000,
//         icon: '⏹️'
//       });
//     }
//   };

//   const handleFileUpload = async (file: File) => {
//     const fileType = file.type;
//     const fileName = file.name.toLowerCase();

//     let type: 'image' | 'pdf' | 'document' = 'document';
//     if (fileType.startsWith('image/')) {
//       type = 'image';
//     } else if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
//       type = 'pdf';
//     }

//     const attachment: FileAttachment = {
//       id: Date.now().toString(),
//       file,
//       type,
//     };

//     if (type === 'image') {
//       const reader = new FileReader();
//       reader.onload = (e) => {
//         attachment.preview = e.target?.result as string;
//         setAttachments(prev => [...prev, attachment]);
//       };
//       reader.readAsDataURL(file);
//     } else {
//       setAttachments(prev => [...prev, attachment]);
//     }

//     toast.success(`${type === 'image' ? 'Image' : type === 'pdf' ? 'PDF' : 'File'} attached successfully!`, {
//       duration: 2000,
//       icon: type === 'image' ? '🖼️' : type === 'pdf' ? '📄' : '📎'
//     });
//   };

//   const handleRemoveAttachment = (id: string) => {
//     setAttachments(prev => prev.filter(att => att.id !== id));
//     toast.success("File removed", {
//       duration: 1500,
//       icon: '🗑️'
//     });
//   };

//   const processAttachments = async (): Promise<string> => {
//     if (attachments.length === 0) return '';

//     let extractedContent = '';

//     for (const attachment of attachments) {
//       try {
//         if (attachment.type === 'image') {
//           toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
//           const result = await scanImageText(attachment.file);
//           if (result.extractedText) {
//             extractedContent += `\n\n[Image: ${attachment.file.name}]\n${result.extractedText}`;
//             toast.success(`Image processed successfully!`, { id: `process-${attachment.id}`, icon: '🖼️' });
//           }
//         } else if (attachment.type === 'pdf') {
//           toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
//           const result = await readPdf(attachment.file);
//           if (result.extractedText) {
//             extractedContent += `\n\n[PDF: ${attachment.file.name}]\n${result.extractedText}`;
//             toast.success(`PDF processed successfully!`, { id: `process-${attachment.id}`, icon: '📄' });
//           }
//         }
//       } catch (error) {
//         console.error(`Error processing ${attachment.file.name}:`, error);
//         toast.error(`Failed to process ${attachment.file.name}`, { id: `process-${attachment.id}` });
//       }
//     }

//     return extractedContent;
//   };

//   return (
//     <div
//       className="chat-container flex flex-col text-white transition-all duration-300 relative overflow-hidden"
//       style={{
//         width: "100%",
//       }}
//     >
//       {/* Selected Guru Display */}
//       {selectedGuru && (
//         <div className="w-full flex justify-center px-3 sm:px-4 pt-4 pb-3 flex-shrink-0">
//           <div className="max-w-md w-full bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10">
//             <div className="flex items-center justify-center gap-3">
//               <div className="relative">
//                 <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-purple-600 rounded-full flex items-center justify-center">
//                   <img src={guruLogo} alt="Guru" className="w-6 h-6" />
//                 </div>
//                 <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-900"></div>
//               </div>
//               <div className="text-center">
//                 <h3 className="text-white font-medium text-sm">
//                   {selectedGuru.name}
//                 </h3>
//                 <p className="text-gray-400 text-xs">
//                   {selectedGuru.subject}
//                 </p>
//               </div>
//               <div className="text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded-full">
//                 Active
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Audio Status Indicator */}
//       {isPlaying && (
//         <div className="w-full flex justify-center px-3 sm:px-4 pb-3 flex-shrink-0">
//           <div className="max-w-sm w-full bg-green-500/10 backdrop-blur-sm rounded-lg p-3 border border-green-400/20">
//             <div className="flex items-center justify-center gap-3">
//               <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
//               <span className="text-green-300 text-sm">Audio playing...</span>
//               <div className="flex items-center space-x-2">
//                 <FontAwesomeIcon
//                   icon={window.speechSynthesis?.paused ? faPlay : faPause}
//                   className="text-green-400 hover:text-green-300 cursor-pointer transition-colors text-sm"
//                   onClick={() => {
//                     if (playingMessageIndex !== null) {
//                       const message = messages[playingMessageIndex];
//                       if (message) {
//                         handleTextToSpeech(message.text, playingMessageIndex);
//                       }
//                     }
//                   }}
//                   title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
//                 />
//                 <FontAwesomeIcon
//                   icon={faStop}
//                   className="text-red-400 hover:text-red-300 cursor-pointer transition-colors text-sm"
//                   onClick={handleStopAudio}
//                   title="Stop audio"
//                 />
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Chat messages */}
//       <div
//         ref={messagesContainerRef}
//         className={`chat-messages-area flex-1 w-full max-w-6xl flex px-4 sm:px-8 py-2 chat-messages-container mx-auto ${
//           messages.length > 0 ? 'flex-col gap-3 sm:gap-4' : 'items-center justify-center lg:min-h-[60vh]'
//         }`}
//         style={{
//           minHeight: 0,
//           overflowY: 'auto',
//           overflowX: 'hidden',
//           scrollbarGutter: 'stable',
//           position: 'relative',
//         }}
//       >
//         {messages.length > 0 ? (
//           messages.map((msg, index) => (
//             <div
//               key={index}
//               className={`flex items-center ${
//                 msg.sender === "user" ? "justify-end" : "justify-start"
//               }`}
//               style={{
//                 width: "100%",
//               }}
//             >
//               {msg.sender === "bot" && (
//                 <img
//                   src={uniguru}
//                   alt="Bot Logo"
//                   className="w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 rounded-full mr-2 sm:mr-3 flex-shrink-0"
//                 />
//               )}
//               <div
//                 className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg relative ${
//                   msg.sender === "bot" && !msg.isLoading ? "flex flex-col" : "flex items-center"
//                 } ${
//                   msg.sender === "user"
//                     ? "bg-[linear-gradient(135deg,_#61ACEF,_#9987ED,_#B679E1,_#9791DB,_#74BDCC,_#59D2BF)] text-black"
//                     : "border border-gray-700 text-white"
//                 }`}
//                 style={{
//                   display: "inline-block",
//                   maxWidth: "85%",
//                   wordWrap: "break-word",
//                   overflowWrap: "break-word",
//                   wordBreak: "break-word",
//                   alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
//                   marginTop: "10px",
//                   fontSize: window.innerWidth < 640 ? "14px" : "16px",
//                   marginBottom: msg.sender === "bot" && !msg.isLoading ? (window.innerWidth < 640 ? "8px" : "20px") : "0px",
//                   position: "relative",
//                 }}
//               >
//                 {msg.isLoading ? (
//                   <div className="flex items-center space-x-3">
//                     <LoadingSpinner size="small" variant="dots" />
//                     <span className="text-purple-300 text-sm">Guru is thinking...</span>
//                   </div>
//                 ) : (
//                   <div className={msg.sender === "bot" ? "w-full" : ""}>
//                     {msg.text}
//                   </div>
//                 )}
//                 {msg.sender === "bot" && !msg.isLoading && (
//                   <div className="mt-2 flex items-center justify-end space-x-2 sm:absolute sm:bottom-[-18px] sm:mt-0 sm:bottom-[-20px] sm:right-0 sm:space-x-1.5 sm:space-x-2">
//                     {/* Audio Controls */}
//                     {isPlaying && playingMessageIndex === index ? (
//                       <div className="flex items-center space-x-1">
//                         <FontAwesomeIcon
//                           icon={window.speechSynthesis?.paused ? faPlay : faPause}
//                           className="text-purple-400 hover:text-purple-300 cursor-pointer transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                           onClick={() => handleTextToSpeech(msg.text, index)}
//                           title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
//                         />
//                         <FontAwesomeIcon
//                           icon={faStop}
//                           className="text-red-400 hover:text-red-300 cursor-pointer transition-colors"
//                           style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                           onClick={handleStopAudio}
//                           title="Stop audio"
//                         />
//                       </div>
//                     ) : (
//                       <FontAwesomeIcon
//                         icon={faVolumeHigh}
//                         className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
//                         style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                         onClick={() => handleTextToSpeech(msg.text, index)}
//                         title="Read aloud"
//                       />
//                     )}
//                     <FontAwesomeIcon
//                       icon={faCopy}
//                       className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
//                       style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
//                       onClick={() => handleCopyMessage(msg.text)}
//                       title="Copy message"
//                     />
//                   </div>
//                 )}
//                 {msg.sender === "bot" && !msg.isLoading && Array.isArray(msg.retrieved_chunks) && msg.retrieved_chunks.length > 0 && (
//                   <div
//                     className="absolute top-2 right-2 flex items-center space-x-1 cursor-pointer"
//                     onClick={() => {
//                       setSidebarChunks(msg.retrieved_chunks || []);
//                       setSidebarOpen(true);
//                       setSelectedChunk(null); // Reset selected chunk when opening sidebar
//                     }}
//                     title={`View ${msg.retrieved_chunks.length} searched chunks`}
//                   >
//                     <FontAwesomeIcon
//                       icon={faMagnifyingGlassChart}
//                       className="text-transparent bg-gradient-to-r from-purple-500 to-blue-500 bg-clip-text hover:from-purple-400 hover:to-blue-400 transition-colors"
//                       style={{ fontSize: window.innerWidth < 640 ? '16px' : '18px' }}
//                     />
//                     <span className="text-purple-400 font-semibold text-xs">{msg.retrieved_chunks.length}</span>
//                   </div>
//                 )}
//               </div>
//               {msg.sender === "user" && (
//                 <img
//                   src={userimage}
//                   alt="User"
//                   className="w-6 h-6 sm:w-8 sm:h-8 rounded-full ml-2 sm:ml-3 flex-shrink-0"
//                 />
//               )}
//             </div>
//           ))
//         ) : (
//           <>
//             {!selectedGuru ? (
//               <div></div>
//             ) : (
//               <div className="text-center">
//                 <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-purple-500/30 to-blue-500/30 rounded-full flex items-center justify-center border border-purple-400/20">
//                   <img src={guruLogo} alt="Guru" className="w-8 h-8" />
//                 </div>
//                 <p className="text-gray-400 text-sm sm:text-base">Ready to chat with {selectedGuru.name}!</p>
//                 <p className="text-gray-500 text-xs sm:text-sm mt-2">Expert in: {selectedGuru.subject}</p>
//               </div>
//             )}
//           </>
//         )}
//         <div ref={messagesEndRef} />
//         <ChunkSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} chunks={sidebarChunks} selectedChunk={selectedChunk} setSelectedChunk={setSelectedChunk} />
//       </div>

//       {/* Fixed Input Area */}
//       {selectedGuru ? (
//         <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 bg-gradient-to-t from-black/20 to-transparent">
//           <div className="w-full max-w-6xl mx-auto px-4 sm:px-8">
//             <EnhancedChatInput
//               message={message}
//               setMessage={setMessage}
//               onSendMessage={handleSendMessage}
//               onKeyDown={handleKeyDown}
//               textareaRef={textareaRef}
//               onFileUpload={handleFileUpload}
//               attachments={attachments}
//               onRemoveAttachment={handleRemoveAttachment}
//             />
//           </div>
//           <div className="text-center text-gray-400 mt-2 text-[10px] xs:text-xs sm:text-sm px-4">
//             Guru can make mistakes. Check important info.
//           </div>
//         </div>
//       ) : (
//         <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 fixed inset-0 flex items-center justify-center pointer-events-none">
//           <div className="w-full max-w-3xl mx-auto px-4 sm:px-8 pointer-events-auto">
//             <div className="bg-gradient-to-br from-white/10 via-white/5 to-transparent backdrop-blur-xl rounded-3xl border border-white/20 p-12 sm:p-16 text-center shadow-2xl shadow-black/20 transform hover:scale-105 transition-all duration-300">
//               <div className="flex items-center justify-center gap-3 mb-6">
//                 <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-lg">
//                   <img src={guruLogo} alt="Guru" className="w-7 h-7" />
//                 </div>
//                 <h4 className="text-white font-semibold text-lg sm:text-xl bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">No guru selected</h4>
//               </div>
//               <p className="text-gray-300 text-sm sm:text-base mb-8 leading-relaxed">
//                 Create or select a guru to start chatting.
//               </p>
//               <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
//                 <button
//                   onClick={() => {
//                     window.dispatchEvent(new CustomEvent('open-guru-create'));
//                   }}
//                   className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-purple-600 via-purple-500 to-blue-600 hover:from-purple-500 hover:via-purple-400 hover:to-blue-500 text-white text-sm font-semibold shadow-xl shadow-purple-500/30 transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 border border-purple-400/30"
//                 >
//                   Create Guru
//                 </button>
//                 <button
//                   onClick={() => {
//                     window.dispatchEvent(new CustomEvent('restart-guru-onboarding'));
//                   }}
//                   className="w-full sm:w-auto px-8 py-3 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 hover:border-white/30 text-white text-sm font-semibold backdrop-blur-sm transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 shadow-lg"
//                 >
//                   How to Guru?
//                 </button>
//               </div>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// };

// export default ChatContainer;



import { useState, useRef, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy, faVolumeHigh, faPause, faPlay, faStop ,faFolderOpen, faMusic, faDownload} from "@fortawesome/free-solid-svg-icons";
import uniguru from "../assets/uni-logo.png";
import userimage from "../assets/userimage.png";
import guruLogo from "../assets/guru.png";

import EnhancedChatInput from "./EnhancedChatInput";
import LoadingSpinner from "./LoadingSpinner";
import ChunkSidebar from "./ChunkSidebar";
import toast from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { useChat } from "../context/ChatContext";
import { useGuru } from "../context/GuruContext";
import { sendChatRequest, getChatSessionById, scanImageText, readPdf } from "../helpers/api-communicator";

interface Message {
  text: string;
  sender: "user" | "bot";
  timestamp?: Date;
  isLoading?: boolean;
  retrieved_chunks?: Array<{ index: number; file: string; score: number; content: string }>;
  metadata?: Record<string, any>;
  vaani_audio?: {
    audio_url?: string;
    error?: string;
  };
}

interface FileAttachment {
  id: string;
  file: File;
  type: 'image' | 'pdf' | 'document';
  preview?: string;
}

const ChatContainer: React.FC = () => {
  const { user } = useAuth();
  const { currentChatId } = useChat();
  const { selectedGuru } = useGuru();

  const [messages, setMessages] = useState<Message[]>([]);
  const [message, setMessage] = useState<string>("");
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [, setCurrentUtterance] = useState<SpeechSynthesisUtterance | null>(null);
  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarChunks, setSidebarChunks] = useState<Array<{ index: number; file: string; score: number; content: string }>>([]);
  const [selectedChunk, setSelectedChunk] = useState<{ index: number; file: string; score: number; content: string } | null>(null);
  // Audio state
  const [playingAudioIndex, setPlayingAudioIndex] = useState<number | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);
  const [vaaniToken, setVaaniToken] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  // Always scroll to bottom for all messages (new and loaded)
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Cleanup audio on component unmount
  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      if (audioElement) {
        audioElement.pause();
        audioElement.currentTime = 0;
      }
    };
  }, [audioElement]);

  // Get Vaani authentication token
  const getVaaniToken = async (): Promise<string | null> => {
    if (vaaniToken) return vaaniToken;

    try {
      const response = await fetch('https://vaani-sentinel-gs6x.onrender.com/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: 'admin',
          password: 'secret'
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const token = data.access_token || data.token;
        if (token) {
          setVaaniToken(token);
          return token;
        }
      }
      console.error('Failed to get Vaani token:', response.status);
      return null;
    } catch (error) {
      console.error('Error getting Vaani token:', error);
      return null;
    }
  };

  // Keyboard shortcuts for audio control
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isPlaying) {
        handleStopAudio();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isPlaying]);

  // Clear messages when guru changes
  useEffect(() => {
    setMessages([]);
    console.log(`Cleared messages due to guru change: ${selectedGuru?.name || 'None'}`);
  }, [selectedGuru]);

  // Load chat history when current chat changes
  useEffect(() => {
    const loadChatHistory = async () => {
      if (currentChatId) {
        try {
          console.log(`Loading chat history for chat ID: ${currentChatId}`);
          const response = await getChatSessionById(currentChatId);
          const chatMessages = response.chat.messages || [];
          const formattedMessages = chatMessages.map((msg: any) => ({
            text: msg.content,
            sender: msg.sender === 'user' ? 'user' : 'bot',
            timestamp: new Date(msg.timestamp),
            retrieved_chunks: msg.metadata && Array.isArray(msg.metadata.retrieved_chunks)
              ? msg.metadata.retrieved_chunks.map((chunk: any) => ({
                  index: chunk.index || 0,
                  file: chunk.file || '',
                  score: chunk.score || 0,
                  content: chunk.content || ''
                }))
              : [],
            metadata: msg.metadata || undefined
          }));
          setMessages(formattedMessages);
          console.log(`Loaded ${formattedMessages.length} messages for chat ${currentChatId}`);

          if (formattedMessages.length > 0) {
            toast.success(`Loaded ${formattedMessages.length} previous messages`, {
              duration: 2000,
              icon: '💬'
            });
          }
        } catch (error) {
          console.error('Error loading chat history:', error);
          toast.error("Failed to load chat history", {
            duration: 2000,
            icon: '⚠️'
          });
          setMessages([]);
        }
      } else {
        console.log('No current chat selected, clearing messages');
        setMessages([]);
      }
    };

    loadChatHistory();
  }, [currentChatId]);

  const handleSendMessage = async () => {
    if ((!message.trim() && attachments.length === 0) || !selectedGuru || !user || isLoading) {
      return;
    }

    const userMessage = message.trim();
    setMessage("");
    setIsLoading(true);

    const attachmentContent = await processAttachments();
    const fullMessage = userMessage + attachmentContent;

    setAttachments([]);

    const newUserMessage: Message = {
      text: userMessage + (attachments.length > 0 ? ` [${attachments.length} file(s) attached]` : ''),
      sender: "user",
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newUserMessage]);

    const loadingMessage: Message = {
      text: "Thinking...",
      sender: "bot",
      timestamp: new Date(),
      isLoading: true
    };
    setMessages(prev => [...prev, loadingMessage]);

    const textarea = document.querySelector("textarea");
    if (textarea) {
      textarea.style.height = "auto";
    }

    try {
      const context = messages
        .slice(-3)
        .filter((msg) => !msg.isLoading)
        .map((msg) => ({
          sender: msg.sender,
          content: msg.text,
          timestamp: msg.timestamp ? new Date(msg.timestamp).toISOString() : new Date().toISOString(),
        }));

      const response = await sendChatRequest(
        fullMessage,
        selectedGuru.id,
        user.id,
        currentChatId || undefined,
        context,
        true // Enable audio generation
      );

      console.log('[DEBUG] sendChatRequest response:', JSON.stringify(response, null, 2));

      if (response.aiResponse) {
        const botMessage: Message = {
          text: response.aiResponse.content || 'No response content',
          sender: "bot",
          timestamp: new Date(),
          retrieved_chunks: Array.isArray(response.aiResponse.metadata?.retrieved_chunks)
            ? response.aiResponse.metadata.retrieved_chunks.map((chunk: any) => ({
                index: chunk.index || 0,
                file: chunk.file || '',
                score: chunk.score || 0,
                content: chunk.content || ''
              }))
            : [],
          metadata: response.aiResponse.metadata || undefined,
          vaani_audio: response.aiResponse.vaani_audio || null
        };

        console.log('[DEBUG] Bot message with chunks:', JSON.stringify(botMessage, null, 2));

        setMessages(prev => {
          const newMessages = [...prev];
          newMessages.pop();
          newMessages.push(botMessage);
          console.log('[DEBUG] Updated messages state:', JSON.stringify(newMessages.slice(-2), null, 2));
          return newMessages;
        });

        if (response.chat && response.chat.id && !currentChatId) {
          console.log(`New chat created with ID: ${response.chat.id}`);
        }
      } else {
        throw new Error('No aiResponse in response');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error("Failed to send message. Please try again.", {
        duration: 3000,
        icon: '❌'
      });

      const errorMessage: Message = {
        text: "Sorry, I'm having trouble responding right now. Please try again.",
        sender: "bot",
        timestamp: new Date(),
        retrieved_chunks: []
      };

      setMessages(prev => {
        const newMessages = [...prev];
        newMessages.pop();
        newMessages.push(errorMessage);
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCopyMessage = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Message copied to clipboard!", {
        duration: 2000,
        icon: '📋'
      });
    } catch (err) {
      console.error('Failed to copy text: ', err);
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      toast.success("Message copied to clipboard!", {
        duration: 2000,
        icon: '📋'
      });
    }
  };

  const handleTextToSpeech = (text: string, messageIndex: number) => {
    if ('speechSynthesis' in window) {
      if (isPlaying && playingMessageIndex === messageIndex) {
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
          toast.success("Audio resumed", {
            duration: 1000,
            icon: '▶️'
          });
        } else {
          window.speechSynthesis.pause();
          toast.success("Audio paused", {
            duration: 1000,
            icon: '⏸️'
          });
        }
        return;
      }

      window.speechSynthesis.cancel();
      setIsPlaying(false);
      setCurrentUtterance(null);
      setPlayingMessageIndex(null);

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 0.8;

      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(voice =>
        voice.name.includes('Google') ||
        voice.name.includes('Microsoft') ||
        voice.lang.startsWith('en')
      );

      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.onstart = () => {
        setIsPlaying(true);
        setCurrentUtterance(utterance);
        setPlayingMessageIndex(messageIndex);
        toast.success("Playing audio...", {
          duration: 1500,
          icon: '🔊'
        });
      };

      utterance.onend = () => {
        setIsPlaying(false);
        setCurrentUtterance(null);
        setPlayingMessageIndex(null);
        toast.success("Audio finished", {
          duration: 1000,
          icon: '✅'
        });
      };

      utterance.onerror = (_event) => {
        setIsPlaying(false);
        setCurrentUtterance(null);
        setPlayingMessageIndex(null);
        toast.error("Failed to play audio", {
          duration: 2000,
          icon: '❌'
        });
      };

      window.speechSynthesis.speak(utterance);
    } else {
      toast.error("Text-to-speech not supported in this browser", {
        duration: 3000,
        icon: '❌'
      });
    }
  };

  const handleStopAudio = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      setCurrentUtterance(null);
      setPlayingMessageIndex(null);
    }
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
      setPlayingAudioIndex(null);
      setAudioElement(null);
    }
    toast.success("Audio stopped", {
      duration: 1000,
      icon: '⏹️'
    });
  };

  const handlePlayVaaniAudio = async (audioUrl: string, messageIndex: number) => {
    if (playingAudioIndex === messageIndex) {
      // If already playing this audio, pause it
      if (audioElement) {
        audioElement.pause();
        setPlayingAudioIndex(null);
        setAudioElement(null);
        toast.success("Audio paused", {
          duration: 1000,
          icon: '⏸️'
        });
      }
      return;
    }

    // Stop any existing audio
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }

    // Stop any TTS
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      setPlayingMessageIndex(null);
    }

    try {
      let finalAudioUrl = audioUrl;

      // If it's a relative URL from Vaani service, construct full URL
      if (audioUrl.startsWith('/api/v1/agents/download-audio/')) {
        finalAudioUrl = `https://vaani-sentinel-gs6x.onrender.com${audioUrl}`;
      }

      // If it's not a data URL, we need to fetch it and convert to base64
      if (!finalAudioUrl.startsWith('data:')) {
        toast.loading("Loading audio...", { id: "audio-loading" });

        // Fetch the audio with authentication
        const token = await getVaaniToken();
        if (!token) {
          throw new Error('Failed to get Vaani authentication token');
        }

        const response = await fetch(finalAudioUrl, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
          }
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch audio: ${response.status}`);
        }

        const audioBuffer = await response.arrayBuffer();
        // Convert ArrayBuffer to base64 using btoa (browser-compatible)
        const uint8Array = new Uint8Array(audioBuffer);
        let binary = '';
        uint8Array.forEach(byte => binary += String.fromCharCode(byte));
        const audioBase64 = btoa(binary);
        const contentType = response.headers.get('content-type') || 'audio/wav';
        finalAudioUrl = `data:${contentType};base64,${audioBase64}`;

        toast.dismiss("audio-loading");
      }

      // Create new audio element
      const audio = new Audio(finalAudioUrl);
      audio.volume = 0.8;

      // Set proper MIME type if it's a data URL
      if (finalAudioUrl.startsWith('data:')) {
        // Extract MIME type from data URL
        const mimeType = finalAudioUrl.split(';')[0].split(':')[1];
        // Note: HTMLAudioElement doesn't have a 'type' property, but we can set it via setAttribute
        audio.setAttribute('type', mimeType);
      }

    audio.onplay = () => {
      setPlayingAudioIndex(messageIndex);
      setAudioElement(audio);
      toast.success("Playing Vaani audio...", {
        duration: 1500,
        icon: '🎵'
      });
    };

    audio.onended = () => {
      setPlayingAudioIndex(null);
      setAudioElement(null);
      toast.success("Audio finished", {
        duration: 1000,
        icon: '✅'
      });
    };

    audio.onerror = (e) => {
      console.error('Audio load error:', e);
      setPlayingAudioIndex(null);
      setAudioElement(null);
      toast.error("Failed to load audio - unsupported format", {
        duration: 3000,
        icon: '❌'
      });
    };

      audio.oncanplay = () => {
        // Audio is ready to play
        console.log('Audio ready to play');
      };

      audio.onloadeddata = () => {
        console.log('Audio data loaded');
      };

      audio.onloadedmetadata = () => {
        console.log('Audio metadata loaded, duration:', audio.duration);
      };

      // Try to play immediately, with fallback
      audio.play().catch((error) => {
        console.error('Audio play error:', error);
        // If immediate play fails, try after loading
        audio.addEventListener('canplay', () => {
          audio.play().catch((retryError) => {
            console.error('Audio retry play error:', retryError);
            toast.error("Failed to play audio - unsupported format or codec", {
              duration: 3000,
              icon: '❌'
            });
          });
        }, { once: true });
      });
    } catch (error) {
      console.error('Error setting up audio:', error);
      toast.error("Failed to load audio", {
        duration: 3000,
        icon: '❌'
      });
    }
  };

  const handleDownloadVaaniAudio = (audioUrl: string, messageIndex: number) => {
    try {
      // Create a temporary anchor element for download
      const link = document.createElement('a');
      link.href = audioUrl;
      link.download = `vaani_audio_${messageIndex}_${Date.now()}.wav`;
      link.target = '_blank';

      // Append to body, click, and remove
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success("Audio download started", {
        duration: 2000,
        icon: '📥'
      });
    } catch (error) {
      console.error('Download error:', error);
      toast.error("Failed to download audio", {
        duration: 2000,
        icon: '❌'
      });
    }
  };

  const handleFileUpload = async (file: File) => {
    const fileType = file.type;
    const fileName = file.name.toLowerCase();

    let type: 'image' | 'pdf' | 'document' = 'document';
    if (fileType.startsWith('image/')) {
      type = 'image';
    } else if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
      type = 'pdf';
    }

    const attachment: FileAttachment = {
      id: Date.now().toString(),
      file,
      type,
    };

    if (type === 'image') {
      const reader = new FileReader();
      reader.onload = (e) => {
        attachment.preview = e.target?.result as string;
        setAttachments(prev => [...prev, attachment]);
      };
      reader.readAsDataURL(file);
    } else {
      setAttachments(prev => [...prev, attachment]);
    }

    toast.success(`${type === 'image' ? 'Image' : type === 'pdf' ? 'PDF' : 'File'} attached successfully!`, {
      duration: 2000,
      icon: type === 'image' ? '🖼️' : type === 'pdf' ? '📄' : '📎'
    });
  };

  const handleRemoveAttachment = (id: string) => {
    setAttachments(prev => prev.filter(att => att.id !== id));
    toast.success("File removed", {
      duration: 1500,
      icon: '🗑️'
    });
  };

  const processAttachments = async (): Promise<string> => {
    if (attachments.length === 0) return '';

    let extractedContent = '';

    for (const attachment of attachments) {
      try {
        if (attachment.type === 'image') {
          toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
          const result = await scanImageText(attachment.file);
          if (result.extractedText) {
            extractedContent += `\n\n[Image: ${attachment.file.name}]\n${result.extractedText}`;
            toast.success(`Image processed successfully!`, { id: `process-${attachment.id}`, icon: '🖼️' });
          }
        } else if (attachment.type === 'pdf') {
          toast.loading(`Processing ${attachment.file.name}...`, { id: `process-${attachment.id}` });
          const result = await readPdf(attachment.file);
          if (result.extractedText) {
            extractedContent += `\n\n[PDF: ${attachment.file.name}]\n${result.extractedText}`;
            toast.success(`PDF processed successfully!`, { id: `process-${attachment.id}`, icon: '📄' });
          }
        }
      } catch (error) {
        console.error(`Error processing ${attachment.file.name}:`, error);
        toast.error(`Failed to process ${attachment.file.name}`, { id: `process-${attachment.id}` });
      }
    }

    return extractedContent;
  };

  // Handle click outside to close sidebar
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (sidebarOpen) {
        const sidebar = document.querySelector('.chunk-sidebar');
        if (sidebar && !sidebar.contains(event.target as Node)) {
          setSidebarOpen(false);
          setSelectedChunk(null);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [sidebarOpen]);

  const renderFormattedBotText = (rawText: string) => {
    const text = (rawText || "").trim();
    if (!text) return null;

    const headingSet = new Set([
      "definitions",
      "key points",
      "concept explanations",
      "light equation context",
      "source(s)",
      "authors",
      "domain",
      "ingestion date",
      "title",
    ]);

    const lines = text.split(/\r?\n/).map((line) => line.trim()).filter((line) => line.length > 0);
    let listKey = 0;

    return (
      <div className="space-y-2">
        {lines.map((line, idx) => {
          const headingMatch = line.match(/^([A-Za-z][A-Za-z\s()/-]{1,40}):\s*(.*)$/);
          const isBullet = /^[-*•]\s+/.test(line);
          const isFormula = /\\sin|\\sqrt|O\([^)]*\)|\bQFT\b|amplitude|theta|\\theta/i.test(line);

          if (headingMatch) {
            const label = headingMatch[1].trim();
            const value = headingMatch[2].trim();
            const isSectionHeading = headingSet.has(label.toLowerCase()) && !value;

            if (isSectionHeading) {
              return (
                <h4 key={`h-${idx}`} className="text-purple-300 font-semibold pt-1">
                  {label}
                </h4>
              );
            }

            return (
              <p key={`kv-${idx}`} className="leading-relaxed">
                <span className="text-purple-300 font-semibold">{label}:</span>{" "}
                <span className="text-gray-100">{value}</span>
              </p>
            );
          }

          if (isBullet) {
            const content = line.replace(/^[-*•]\s+/, "");
            listKey += 1;
            return (
              <div key={`b-${idx}-${listKey}`} className="flex gap-2 leading-relaxed">
                <span className="text-purple-300">•</span>
                <span className={isFormula ? "font-mono text-cyan-200 text-sm" : "text-gray-100"}>{content}</span>
              </div>
            );
          }

          return (
            <p
              key={`p-${idx}`}
              className={`${isFormula ? "font-mono text-cyan-200 text-sm" : "text-gray-100"} leading-relaxed whitespace-pre-wrap`}
            >
              {line}
            </p>
          );
        })}
      </div>
    );
  };

  const renderGovernancePanel = (metadata?: Record<string, any>) => {
    if (!metadata?.trace_id) return null;
    const confidence = Number(metadata.confidence_breakdown?.overall || 0);
    const contradictions = metadata.consensus_analysis?.contradictions || [];
    const acceptedCount = Array.isArray(metadata.matched_signals) ? metadata.matched_signals.length : 0;
    const rejectedCount = Array.isArray(metadata.rejected_signals) ? metadata.rejected_signals.length : 0;
    const lineage = metadata.retrieval_truth_payload?.source_lineage || [];
    const memoryEvent = metadata.semantic_memory?.event || {};
    const traversalPath = metadata.multi_hop_traversal?.paths?.[0] || [];
    const downstreamStatus = metadata.downstream_execution?.status || "UNKNOWN";

    return (
      <div className="mt-3 w-full rounded-md border border-cyan-400/20 bg-slate-950/70 p-3 text-xs text-gray-200">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div>
            <div className="text-gray-400">Confidence</div>
            <div className={confidence >= 0.6 ? "text-emerald-300 font-semibold" : "text-amber-300 font-semibold"}>
              {(confidence * 100).toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-gray-400">Contradiction</div>
            <div className={contradictions.length ? "text-red-300 font-semibold" : "text-emerald-300 font-semibold"}>
              {contradictions.length ? `${contradictions.length} visible` : "none detected"}
            </div>
          </div>
          <div>
            <div className="text-gray-400">Signals</div>
            <div className="font-semibold text-cyan-200">{acceptedCount} accepted / {rejectedCount} rejected</div>
          </div>
          <div>
            <div className="text-gray-400">Downstream</div>
            <div className="font-semibold text-cyan-200">{downstreamStatus}</div>
          </div>
        </div>
        <div className="mt-2 border-t border-white/10 pt-2">
          <div className="text-gray-400">Trace</div>
          <div className="break-all font-mono text-cyan-200">{metadata.trace_id}</div>
        </div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          <div>
            <div className="text-gray-400">Truth Boundary</div>
            <div>retrieval: {metadata.retrieval_truth_payload?.artifact_hash?.slice(0, 12) || "missing"}</div>
            <div>interpretation: {metadata.interpretation_payload?.artifact_hash?.slice(0, 12) || "missing"}</div>
          </div>
          <div>
            <div className="text-gray-400">Memory</div>
            <div>{memoryEvent.entities_touched?.length || 0} entities touched</div>
            <div>{metadata.semantic_memory?.unresolved_threads?.length || 0} unresolved threads</div>
          </div>
        </div>
        {lineage.length > 0 && (
          <div className="mt-2">
            <div className="text-gray-400">Source Lineage</div>
            <div className="space-y-1">
              {lineage.slice(0, 3).map((item: any, idx: number) => (
                <div key={`${item.signal_id || idx}`} className="break-words">
                  {item.signal_id} - {item.source || "unknown source"}
                </div>
              ))}
            </div>
          </div>
        )}
        {traversalPath.length > 0 && (
          <div className="mt-2">
            <div className="text-gray-400">Semantic Traversal</div>
            <div className="break-words text-cyan-100">
              {traversalPath.map((hop: any) => hop.node).join(" -> ")}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      className="chat-container flex flex-col text-white transition-all duration-300 relative overflow-hidden"
      style={{
        width: "100%",
      }}
    >
      {/* Selected Guru Display */}
      {selectedGuru && (
        <div className="w-full flex justify-center px-3 sm:px-4 pt-4 pb-3 flex-shrink-0">
          <div className="max-w-md w-full bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10">
            <div className="flex items-center justify-center gap-3">
              <div className="relative">
                <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-purple-600 rounded-full flex items-center justify-center">
                  <img src={guruLogo} alt="Guru" className="w-6 h-6" />
                </div>
                <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-900"></div>
              </div>
              <div className="text-center">
                <h3 className="text-white font-medium text-sm">
                  {selectedGuru.name}
                </h3>
                <p className="text-gray-400 text-xs">
                  {selectedGuru.subject}
                </p>
              </div>
              <div className="text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded-full">
                Active
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Audio Status Indicator */}
      {isPlaying && (
        <div className="w-full flex justify-center px-3 sm:px-4 pb-3 flex-shrink-0">
          <div className="max-w-sm w-full bg-green-500/10 backdrop-blur-sm rounded-lg p-3 border border-green-400/20">
            <div className="flex items-center justify-center gap-3">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-green-300 text-sm">Audio playing...</span>
              <div className="flex items-center space-x-2">
                <FontAwesomeIcon
                  icon={window.speechSynthesis?.paused ? faPlay : faPause}
                  className="text-green-400 hover:text-green-300 cursor-pointer transition-colors text-sm"
                  onClick={() => {
                    if (playingMessageIndex !== null) {
                      const message = messages[playingMessageIndex];
                      if (message) {
                        handleTextToSpeech(message.text, playingMessageIndex);
                      }
                    }
                  }}
                  title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
                />
                <FontAwesomeIcon
                  icon={faStop}
                  className="text-red-400 hover:text-red-300 cursor-pointer transition-colors text-sm"
                  onClick={handleStopAudio}
                  title="Stop audio"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chat messages */}
      <div
        ref={messagesContainerRef}
        className={`chat-messages-area flex-1 w-full max-w-6xl flex px-4 sm:px-8 py-2 chat-messages-container mx-auto ${
          messages.length > 0 ? 'flex-col gap-3 sm:gap-4' : 'items-center justify-center lg:min-h-[60vh]'
        }`}
        style={{
          minHeight: 0,
          overflowY: 'auto',
          overflowX: 'hidden',
          scrollbarGutter: 'stable',
          position: 'relative',
        }}
      >
        {messages.length > 0 ? (
          messages.map((msg, index) => (
            <div
              key={index}
              className={`flex items-center ${
                msg.sender === "user" ? "justify-end" : "justify-start"
              }`}
              style={{
                width: "100%",
              }}
            >
              {msg.sender === "bot" && (
                <img
                  src={uniguru}
                  alt="Bot Logo"
                  className="w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 rounded-full mr-2 sm:mr-3 flex-shrink-0"
                />
              )}
              <div
                className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg relative ${
                  msg.sender === "bot" && !msg.isLoading ? "flex flex-col" : "flex items-center"
                } ${
                  msg.sender === "user"
                    ? "bg-[linear-gradient(135deg,_#61ACEF,_#9987ED,_#B679E1,_#9791DB,_#74BDCC,_#59D2BF)] text-black"
                    : "border border-gray-700 text-white"
                }`}
                style={{
                  display: "inline-block",
                  maxWidth: "85%",
                  wordWrap: "break-word",
                  overflowWrap: "break-word",
                  wordBreak: "break-word",
                  alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
                  marginTop: "10px",
                  fontSize: window.innerWidth < 640 ? "14px" : "16px",
                  marginBottom: msg.sender === "bot" && !msg.isLoading ? (window.innerWidth < 640 ? "8px" : "20px") : "0px",
                  position: "relative",
                }}
              >
                {msg.isLoading ? (
                  <div className="flex items-center space-x-3">
                    <LoadingSpinner size="small" variant="dots" />
                    <span className="text-purple-300 text-sm">Guru is thinking...</span>
                  </div>
                ) : (
                  <div className={msg.sender === "bot" ? "w-full" : ""}>
                    {msg.sender === "bot" ? renderFormattedBotText(msg.text) : msg.text}
                    {msg.sender === "bot" && renderGovernancePanel(msg.metadata)}
                  </div>
                )}
                {msg.sender === "bot" && !msg.isLoading && (
                  <div className="mt-2 flex items-center justify-end space-x-2 sm:absolute sm:bottom-[-18px] sm:mt-0 sm:bottom-[-20px] sm:right-0 sm:space-x-1.5 sm:space-x-2">
                    {/* Audio Controls */}
                    {isPlaying && playingMessageIndex === index ? (
                      <div className="flex items-center space-x-1">
                        <FontAwesomeIcon
                          icon={window.speechSynthesis?.paused ? faPlay : faPause}
                          className="text-purple-400 hover:text-purple-300 cursor-pointer transition-colors"
                          style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
                          onClick={() => handleTextToSpeech(msg.text, index)}
                          title={window.speechSynthesis?.paused ? "Resume audio" : "Pause audio"}
                        />
                        <FontAwesomeIcon
                          icon={faStop}
                          className="text-red-400 hover:text-red-300 cursor-pointer transition-colors"
                          style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
                          onClick={handleStopAudio}
                          title="Stop audio"
                        />
                      </div>
                    ) : (
                      <FontAwesomeIcon
                        icon={faVolumeHigh}
                        className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
                        style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
                        onClick={() => handleTextToSpeech(msg.text, index)}
                        title="Read aloud"
                      />
                    )}
                    <FontAwesomeIcon
                      icon={faCopy}
                      className="text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
                      style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
                      onClick={() => handleCopyMessage(msg.text)}
                      title="Copy message"
                    />
                    {/* Vaani Audio Controls */}
                    {msg.vaani_audio && msg.vaani_audio.audio_url && (
                      <div className="flex items-center space-x-1">
                        <FontAwesomeIcon
                          icon={playingAudioIndex === index ? faPause : faMusic}
                          className="text-gray-400 hover:text-green-400 cursor-pointer transition-colors"
                          style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
                          onClick={() => handlePlayVaaniAudio(msg.vaani_audio!.audio_url!, index)}
                          title={playingAudioIndex === index ? "Pause Vaani audio" : "Play Vaani audio"}
                        />
                        <FontAwesomeIcon
                          icon={faDownload}
                          className="text-gray-400 hover:text-blue-400 cursor-pointer transition-colors"
                          style={{ fontSize: window.innerWidth < 640 ? '12px' : '14px' }}
                          onClick={() => handleDownloadVaaniAudio(msg.vaani_audio!.audio_url!, index)}
                          title="Download Vaani audio"
                        />
                      </div>
                    )}
                  </div>
                )}
              {msg.sender === "bot" && !msg.isLoading && Array.isArray(msg.retrieved_chunks) && msg.retrieved_chunks.length > 0 && (
                <div
                  className="mt-2 flex items-center justify-center cursor-pointer"
                  onClick={() => {
                    setSidebarChunks(msg.retrieved_chunks || []);
                    setSidebarOpen(true);
                    setSelectedChunk(null); // Reset selected chunk when opening sidebar
                  }}
                  title={`View ${msg.retrieved_chunks.length} searched chunks`}
                >
                  <FontAwesomeIcon
                    icon={faFolderOpen}
                    className="text-transparent bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text hover:from-teal-400 hover:to-cyan-400 transition-colors"
                    style={{ fontSize: window.innerWidth < 640 ? '20px' : '24px' }}
                  />
                 <span className="text-teal-400 font-semibold text-sm ml-2 flex items-center">
                  Researched on {msg.retrieved_chunks.length} chunks
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="ml-1 h-4 w-4 text-teal-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"
                    />
                  </svg>
                </span>    </div>
              )}

              </div>
              {msg.sender === "user" && (
                <img
                  src={userimage}
                  alt="User"
                  className="w-6 h-6 sm:w-8 sm:h-8 rounded-full ml-2 sm:ml-3 flex-shrink-0"
                />
              )}
            </div>
          ))
        ) : (
          <>
            {!selectedGuru ? (
              <div></div>
            ) : (
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-purple-500/30 to-blue-500/30 rounded-full flex items-center justify-center border border-purple-400/20">
                  <img src={guruLogo} alt="Guru" className="w-8 h-8" />
                </div>
                <p className="text-gray-400 text-sm sm:text-base">Ready to chat with {selectedGuru.name}!</p>
                <p className="text-gray-500 text-xs sm:text-sm mt-2">Expert in: {selectedGuru.subject}</p>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
        <ChunkSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} chunks={sidebarChunks} selectedChunk={selectedChunk} setSelectedChunk={setSelectedChunk} />
      </div>

      {/* Fixed Input Area */}
      {selectedGuru ? (
        <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 bg-gradient-to-t from-black/20 to-transparent">
          <div className="w-full max-w-6xl mx-auto px-4 sm:px-8">
            <EnhancedChatInput
              message={message}
              setMessage={setMessage}
              onSendMessage={handleSendMessage}
              onKeyDown={handleKeyDown}
              textareaRef={textareaRef}
              onFileUpload={handleFileUpload}
              attachments={attachments}
              onRemoveAttachment={handleRemoveAttachment}
            />
          </div>
          <div className="text-center text-gray-400 mt-2 text-[10px] xs:text-xs sm:text-sm px-4">
            Guru can make mistakes. Check important info.
          </div>
        </div>
      ) : (
        <div className="chat-input-area flex-shrink-0 w-full pt-3 pb-4 fixed inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-full max-w-3xl mx-auto px-4 sm:px-8 pointer-events-auto">
            <div className="bg-gradient-to-br from-white/10 via-white/5 to-transparent backdrop-blur-xl rounded-3xl border border-white/20 p-12 sm:p-16 text-center shadow-2xl shadow-black/20 transform hover:scale-105 transition-all duration-300">
              <div className="flex items-center justify-center gap-3 mb-6">
                <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-lg">
                  <img src={guruLogo} alt="Guru" className="w-7 h-7" />
                </div>
                <h4 className="text-white font-semibold text-lg sm:text-xl bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">No guru selected</h4>
              </div>
              <p className="text-gray-300 text-sm sm:text-base mb-8 leading-relaxed">
                Create or select a guru to start chatting.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <button
                  onClick={() => {
                    window.dispatchEvent(new CustomEvent('open-guru-create'));
                  }}
                  className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-purple-600 via-purple-500 to-blue-600 hover:from-purple-500 hover:via-purple-400 hover:to-blue-500 text-white text-sm font-semibold shadow-xl shadow-purple-500/30 transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 border border-purple-400/30"
                >
                  Create Guru
                </button>
                <button
                  onClick={() => {
                    window.dispatchEvent(new CustomEvent('restart-guru-onboarding'));
                  }}
                  className="w-full sm:w-auto px-8 py-3 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 hover:border-white/30 text-white text-sm font-semibold backdrop-blur-sm transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 shadow-lg"
                >
                  How to Guru?
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatContainer;
