import React, { createContext, useContext, useState, useEffect } from 'react';
import { getUserChatSessions, createNewChatSession, deleteChatSession, updateChatSession, getAllChatsWithData } from '../helpers/api-communicator';
import { useAuth } from './AuthContext';
import { useGuru } from './GuruContext';

export interface ChatSession {
  id: string;
  title: string;
  guru: {
    _id: string;
    name: string;
    subject: string;
    description: string;
  };
  createdAt: string;
  messageCount: number;
  lastActivity: string;
  isActive: boolean;
}

interface ChatContextType {
  chatSessions: ChatSession[];
  currentChatId: string | null;
  isLoading: boolean;
  error: string | null;

  // Chat session management
  createNewChat: (guruId: string, title?: string) => Promise<ChatSession>;
  loadChatSessions: (guruId?: string) => Promise<void>;
  loadAllChats: () => Promise<void>;
  selectChat: (chatId: string) => void;
  updateChat: (chatId: string, updates: { title?: string; isArchived?: boolean }) => Promise<void>;
  deleteChat: (chatId: string) => Promise<void>;

  // Current chat helpers
  getCurrentChat: () => ChatSession | null;
  getChatsByGuru: (guruId: string) => ChatSession[];

  // Auto-loading and initialization
  initializeChats: () => Promise<void>;

  // Chat management
  renameChat: (chatId: string, newTitle: string) => Promise<void>;
  ensureActiveChat: () => Promise<void>;
  createNewChatManually: (guruId?: string) => Promise<void>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

interface ChatProviderProps {
  children: React.ReactNode;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(() => {
    // Restore current chat ID from localStorage on initialization
    try {
      return localStorage.getItem('uniguru_current_chat_id') || null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { user, isLoggedIn } = useAuth();
  const { selectedGuru } = useGuru();

  // Initialize chats when user logs in
  useEffect(() => {
    if (user && isLoggedIn) {
      initializeChats();
    } else {
      // Clear chats when user is not authenticated
      setChatSessions([]);
      setCurrentChatId(null);
      localStorage.removeItem('uniguru_current_chat_id');
    }
  }, [user, isLoggedIn]);

  // Auto-select most recent chat when guru changes (but don't auto-create)
  useEffect(() => {
    if (selectedGuru && chatSessions.length >= 0) {
      const guruChats = getChatsByGuru(selectedGuru.id);
      if (guruChats.length > 0) {
        // Select the most recent chat for this guru
        setCurrentChatId(guruChats[0].id);
        console.log(`Auto-selected chat ${guruChats[0].id} for guru ${selectedGuru.name}`);
      } else {
        // No chats for this guru, clear current chat (don't auto-create)
        setCurrentChatId(null);
        localStorage.removeItem('uniguru_current_chat_id');
        console.log(`No chats found for guru ${selectedGuru.name}, cleared current chat`);
      }
    } else if (!selectedGuru) {
      // No guru selected, clear current chat
      setCurrentChatId(null);
      localStorage.removeItem('uniguru_current_chat_id');
      console.log(`No guru selected, cleared current chat`);
    }
  }, [selectedGuru, chatSessions]);

  const createNewChat = async (guruId: string, title?: string): Promise<ChatSession> => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await createNewChatSession(guruId, title);
      const newChat: ChatSession = {
        id: response.chat.id,
        title: response.chat.title,
        guru: response.chat.guru,
        createdAt: response.chat.createdAt,
        messageCount: response.chat.messageCount || 0,
        lastActivity: response.chat.lastActivity,
        isActive: true
      };
      
      setChatSessions(prev => [newChat, ...prev]);
      setCurrentChatId(newChat.id);
      
      return newChat;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create new chat';
      setError(errorMessage);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const initializeChats = async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await getAllChatsWithData(false); // Don't include messages for initial load
      setChatSessions(response.chats || []);

      // Validate stored current chat ID
      if (currentChatId && response.chats) {
        const chatExists = response.chats.some((chat: any) => chat.id === currentChatId);
        if (chatExists) {
          console.log(`Restored current chat from localStorage: ${currentChatId}`);
        } else {
          console.log(`Stored chat ID ${currentChatId} no longer exists, clearing`);
          setCurrentChatId(null);
          localStorage.removeItem('uniguru_current_chat_id');
        }
      }

      // Auto-select the most recent chat if none is selected and chats exist
      if (!currentChatId && response.chats && response.chats.length > 0) {
        const mostRecentChat = response.chats[0];
        setCurrentChatId(mostRecentChat.id);
        localStorage.setItem('uniguru_current_chat_id', mostRecentChat.id);
        console.log(`Auto-selected most recent chat: ${mostRecentChat.id}`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to initialize chats';
      setError(errorMessage);
      console.error('Error initializing chats:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadAllChats = async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await getAllChatsWithData(false);
      setChatSessions(response.chats || []);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load all chats';
      setError(errorMessage);
      console.error('Error loading all chats:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadChatSessions = async (guruId?: string): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await getUserChatSessions(guruId);

      if (guruId) {
        // If loading for specific guru, update only those chats
        setChatSessions(prev => {
          const otherChats = prev.filter(chat => chat.guru._id !== guruId);
          return [...otherChats, ...(response.chats || [])];
        });
      } else {
        setChatSessions(response.chats || []);
      }

      // If no current chat selected and there are chats, select the most recent one
      if (!currentChatId && response.chats && response.chats.length > 0) {
        setCurrentChatId(response.chats[0].id);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load chat sessions';
      setError(errorMessage);
      console.error('Error loading chat sessions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const selectChat = (chatId: string) => {
    setCurrentChatId(chatId);
    // Save to localStorage for persistence across refreshes
    try {
      localStorage.setItem('uniguru_current_chat_id', chatId);
      console.log(`Saved current chat ID to localStorage: ${chatId}`);
    } catch (error) {
      console.warn('Failed to save current chat ID to localStorage:', error);
    }
  };

  const updateChat = async (chatId: string, updates: { title?: string; isArchived?: boolean }): Promise<void> => {
    try {
      setError(null);
      
      await updateChatSession(chatId, updates);
      
      setChatSessions(prev => 
        prev.map(chat => 
          chat.id === chatId 
            ? { ...chat, ...updates }
            : chat
        )
      );
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update chat';
      setError(errorMessage);
      throw error;
    }
  };

  const deleteChat = async (chatId: string): Promise<void> => {
    try {
      setError(null);

      console.log(`🗑️ ChatContext: Starting deletion of chat: ${chatId}`);
      console.log(`📊 Current chat sessions count: ${chatSessions.length}`);
      console.log(`🎯 Current active chat: ${currentChatId}`);

      // Call the API to delete the chat
      await deleteChatSession(chatId);
      console.log(`✅ ChatContext: Chat ${chatId} deleted successfully from backend`);

      // Update chat sessions and handle current chat selection
      setChatSessions(prev => {
        console.log(`🔄 ChatContext: Updating chat sessions, removing chat ${chatId}`);
        const updatedChats = prev.filter(chat => chat.id !== chatId);
        console.log(`📊 ChatContext: Updated chat sessions count: ${updatedChats.length}`);

        // If the deleted chat was the current one, select another or clear selection
        if (currentChatId === chatId) {
          console.log(`🎯 ChatContext: Deleted chat was the current one, selecting new chat`);
          if (updatedChats.length > 0) {
            // Select the most recent remaining chat
            const newChatId = updatedChats[0].id;
            setCurrentChatId(newChatId);
            localStorage.setItem('uniguru_current_chat_id', newChatId);
            console.log(`✅ ChatContext: Selected new current chat: ${newChatId}`);
          } else {
            // No chats left, clear current chat
            setCurrentChatId(null);
            localStorage.removeItem('uniguru_current_chat_id');
            console.log(`🚫 ChatContext: No chats remaining, cleared current chat`);
          }
        }

        return updatedChats;
      });

      console.log(`🎉 ChatContext: Chat deletion completed successfully`);

    } catch (error) {
      console.error('❌ ChatContext: Error deleting chat:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete chat';
      setError(errorMessage);
      throw error;
    }
  };

  const renameChat = async (chatId: string, newTitle: string): Promise<void> => {
    try {
      setError(null);

      console.log(`✏️ ChatContext: Starting rename of chat ${chatId} to "${newTitle}"`);
      console.log(`📊 ChatContext: Current chat sessions count: ${chatSessions.length}`);

      await updateChatSession(chatId, { title: newTitle.trim() });
      console.log(`✅ ChatContext: Chat ${chatId} renamed successfully in backend`);

      // Update the chat in local state
      setChatSessions(prev => {
        console.log(`🔄 ChatContext: Updating chat sessions, renaming chat ${chatId}`);
        const updatedChats = prev.map(chat =>
          chat.id === chatId
            ? { ...chat, title: newTitle.trim() }
            : chat
        );
        console.log(`✅ ChatContext: Local state updated for chat ${chatId}`);
        return updatedChats;
      });

      console.log(`🎉 ChatContext: Chat rename completed successfully`);
    } catch (error) {
      console.error('❌ ChatContext: Error renaming chat:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to rename chat';
      setError(errorMessage);
      throw error;
    }
  };

  const ensureActiveChat = async (): Promise<void> => {
    if (!selectedGuru) return;

    try {
      // Check if there's already an active chat for this guru
      const guruChats = getChatsByGuru(selectedGuru.id);

      // Only create a new chat if this is the first time and no chats exist
      if (guruChats.length === 0 && chatSessions.length === 0) {
        console.log(`First time user - creating initial chat for guru: ${selectedGuru.name}`);
        const newChat = await createNewChat(selectedGuru.id, `New Chat`);
        console.log(`Created initial chat: ${newChat.id}`);
      }
    } catch (error) {
      console.error('Error ensuring active chat:', error);
      // Don't throw error to avoid breaking the app
    }
  };

  const createNewChatManually = async (guruId?: string): Promise<void> => {
    const targetGuruId = guruId || selectedGuru?.id;
    if (!targetGuruId) {
      throw new Error('No guru selected');
    }

    try {
      console.log(`Manually creating new chat for guru: ${targetGuruId}`);
      const newChat = await createNewChat(targetGuruId, `New Chat`);
      console.log(`Manually created new chat: ${newChat.id}`);

      // Auto-select the new chat and save to localStorage
      setCurrentChatId(newChat.id);
      try {
        localStorage.setItem('uniguru_current_chat_id', newChat.id);
        console.log(`Saved new chat ID to localStorage: ${newChat.id}`);
      } catch (error) {
        console.warn('Failed to save new chat ID to localStorage:', error);
      }
    } catch (error) {
      console.error('Error creating new chat manually:', error);
      throw error;
    }
  };

  const getCurrentChat = (): ChatSession | null => {
    return chatSessions.find(chat => chat.id === currentChatId) || null;
  };

  const getChatsByGuru = (guruId: string): ChatSession[] => {
    return chatSessions.filter(chat => chat.guru._id === guruId);
  };

  const value: ChatContextType = {
    chatSessions,
    currentChatId,
    isLoading,
    error,
    createNewChat,
    loadChatSessions,
    loadAllChats,
    selectChat,
    updateChat,
    deleteChat,
    renameChat,
    ensureActiveChat,
    createNewChatManually,
    getCurrentChat,
    getChatsByGuru,
    initializeChats
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};
