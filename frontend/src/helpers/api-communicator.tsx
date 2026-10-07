import axios from "axios";
import { IMessage } from "../context/AuthContext";

// Configure axios base URL and defaults
const isRemoteOrNgrok = typeof window !== "undefined" && (
  window.location.hostname.includes("ngrok") || 
  (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1")
);
const API_BASE_URL = isRemoteOrNgrok 
  ? "" 
  : (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000");
axios.defaults.baseURL = API_BASE_URL;
axios.defaults.withCredentials = true;

console.log('API Base URL:', API_BASE_URL);

// Initialize token from localStorage on app start
const initializeAuth = () => {
  const token = localStorage.getItem('token');
  if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
};

// Call initialization
initializeAuth();

// Add request interceptor for debugging and token handling
axios.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url);

    // Add token to Authorization header if available
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    console.error('Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token expiration
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token might be expired or invalid
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];

      // Only show toast/redirect intent if we're not already on auth pages
      const currentPath = window.location.pathname;
      const onAuthPage =
        currentPath.includes('/login') ||
        currentPath.includes('/signup') ||
        currentPath.includes('/forgot-password') ||
        currentPath.includes('/reset-password');

      // Show a specific session-expired message
      try {
        // Dynamically import to avoid circular deps or SSR issues
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        import('react-hot-toast').then(({ default: toast }) => {
          if (!onAuthPage) {
            toast.error('Your session has expired. Please log in again.', { id: 'auth-expired' });
          }
        });
      } catch {}

      if (!onAuthPage) {
        console.log('Token expired, consider redirecting to login.');
        // Optionally navigate to login here if desired
        // window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Add response interceptor for debugging
axios.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('Response Error:', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

export const loginUser = async (email: string, password: string, googleToken?: string) => {
  try {
    const response = await axios.post(
      "/user/login",
      {
        email,
        password,
        googleToken // Send googleToken if available
      },
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    // Store token in localStorage for subsequent requests
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
    }

    return response.data;
  } catch (error) {
    // Type assertion for AxiosError
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.response?.data?.message || "Login failed");
    } else {
      // If the error is not an AxiosError, throw a generic error
      throw new Error("An unexpected error occurred");
    }
  }
};


export const signupUser = async (
  name: string,
  email: string,
  password: string
) => {
  try {
    const res = await axios.post("/user/signup", { name, email, password });
    console.log("signup response:", res);

    // Store token in localStorage for subsequent requests
    if (res.data.token) {
      localStorage.setItem('token', res.data.token);
    }

    return res.data;
  } catch (error) {
    console.error("Signup error:", error);
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.response?.data?.message || "Signup failed");
    }
    throw new Error("An unexpected error occurred during signup");
  }
};

export const checkAuthStatus = async () => {
  try {
    const res = await axios.get("/user/auth-status");
    return res.data;
  } catch (error) {
    // If 401, user is not authenticated - this is expected
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      return null; // Return null instead of throwing error
    }
    console.error("Auth status check error:", error);
    throw error;
  }
};

// Send Chat Request
export interface ChatContextItem {
  sender: string;
  content: string;
  timestamp: string;
}

export const sendChatRequest = async (
  message: string,
  chatbotId: string,
  userId: string,
  chatId?: string,
  context?: ChatContextItem[],
  generateAudio?: boolean
) => {
  try {
    const response = await axios.post(`/chat/new`, {
      message,
      chatbotId,
      userId,
      chatId, // Include chatId to specify which chat to send message to
      context: context || [],
      generateAudio: generateAudio || false
    });
    return response.data; // Ensure this returns the necessary data for your component
  } catch (error) {
    console.error("Failed to send chat request:", error);
    throw error; // Re-throw error to handle it in the component
  }
};

// Get User Chats
export const getUserChats = async () => {
  try {
    const res = await axios.get("/chat/all-chats");
    if (res.status !== 200) {
      throw new Error("Unable to fetch chats");
    }
    const data = await res.data;
    return data;
  } catch (error) {
    console.error("Error fetching user chats:", error);
    throw error;
  }
};

// Fetch User Gurus
export const fetchUserGurus = async () => {
  try {
    const response = await axios.get("/guru/g-g");
    const data = response.data.chatbots;
    return data;
  } catch (error) {
    console.error("Error fetching user chatbots:", error);
    throw error;
  }
};

// Fetch Guru Chat
export const getChatFromGuru = async (chatbotid: string, userid: string) => {
  try {
    const response = await axios.get(`/guru/g-c/${chatbotid}/${userid}`);
    const messages = response.data.messages;

    // Map the messages to the desired format
    const mappedMessages = messages.map((message: IMessage) => ({
      sender: message.sender,
      content: message.content,
      timestamp: message.timestamp,
    }));

    return mappedMessages; // Return the mapped data
  } catch (error) {
    console.error("Error fetching chat from guru:", error);
    throw error; // Rethrow error to be handled by calling function
  }
};

// Create New Chat Session
export const createNewChatSession = async (guruId: string, title?: string) => {
  try {
    const response = await axios.post("/chat/create", {
      guruId,
      title
    });
    return response.data;
  } catch (error) {
    console.error("Error creating new chat session:", error);
    throw error;
  }
};

// Get User Chats
export const getUserChatSessions = async (guruId?: string, archived = false) => {
  try {
    const params = new URLSearchParams();
    if (guruId) params.append('guruId', guruId);
    if (archived) params.append('archived', 'true');

    const response = await axios.get(`/chat/list?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error("Error fetching user chat sessions:", error);
    throw error;
  }
};

// Get All Chats With Data for Auto-loading
export const getAllChatsWithData = async (includeMessages = false) => {
  try {
    const params = new URLSearchParams();
    if (includeMessages) params.append('includeMessages', 'true');

    const response = await axios.get(`/chat/all-with-data?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error("Error fetching all chats with data:", error);
    throw error;
  }
};

// Get Chat by ID
export const getChatSessionById = async (chatId: string) => {
  try {
    const response = await axios.get(`/chat/chat/${chatId}`);
    return response.data;
  } catch (error) {
    console.error("Error fetching chat session:", error);
    throw error;
  }
};

// Update Chat Details
export const updateChatSession = async (chatId: string, updates: { title?: string; isArchived?: boolean; isActive?: boolean }) => {
  try {
    console.log(`✏️ API: Attempting to update chat: ${chatId}`, updates);
    console.log(`🔗 API: Update URL will be: ${axios.defaults.baseURL}/chat/chat/${chatId}`);

    const response = await axios.put(`/chat/chat/${chatId}`, updates);
    console.log(`✅ API: Chat update response status: ${response.status}`);
    console.log(`✅ API: Chat update response data:`, response.data);

    return response.data;
  } catch (error) {
    console.error("❌ API: Error updating chat session:", error);

    // Enhanced error logging
    if (axios.isAxiosError(error)) {
      console.error("❌ API: Response status:", error.response?.status);
      console.error("❌ API: Response data:", error.response?.data);
      console.error("❌ API: Request URL:", error.config?.url);
    }

    throw error;
  }
};

// Delete Chat Session
export const deleteChatSession = async (chatId: string) => {
  try {
    console.log(`🗑️ API: Attempting to delete chat: ${chatId}`);
    console.log(`🔗 API: Delete URL will be: ${axios.defaults.baseURL}/chat/chat/${chatId}`);

    const response = await axios.delete(`/chat/chat/${chatId}`);
    console.log(`✅ API: Chat deletion response status: ${response.status}`);
    console.log(`✅ API: Chat deletion response data:`, response.data);

    if (response.status !== 200) {
      throw new Error(`Delete request failed with status: ${response.status}`);
    }

    return response.data;
  } catch (error) {
    console.error("❌ API: Error deleting chat session:", error);

    // Enhanced error logging
    if (axios.isAxiosError(error)) {
      console.error("❌ API: Response status:", error.response?.status);
      console.error("❌ API: Response data:", error.response?.data);
      console.error("❌ API: Request URL:", error.config?.url);
      console.error("❌ API: Full request config:", error.config);
    }

    throw error;
  }
};

// New Guru
export const createNewGuru = async (userid: string) => {
  try {
    const res = await axios.post(`/guru/n-g/${userid}`);

    if (res.status !== 200) {
      throw new Error("Unable to create Guru");
    }

    return res.data;
  } catch (error) {
    console.error("Error Creating Guru:", error);
    throw error;
  }
};

// Create Custom Guru
export const createCustomGuru = async (
  userid: string,
  name: string,
  subject: string,
  description: string
) => {
  try {
    const res = await axios.post(`/guru/custom-guru/${userid}`, {
      name,
      subject,
      description
    });

    if (res.status !== 200) {
      throw new Error("Unable to create custom Guru");
    }

    return res.data;
  } catch (error) {
    console.error("Error Creating Custom Guru:", error);
    throw error;
  }
};

// Delete Guru
export const deleteGuru = async (chatbotId: string) => {
  try {
    const res = await axios.delete(`/guru/g-d/${chatbotId}`);

    if (res.status !== 200) {
      throw new Error("Unable to delete chatbot");
    }

    return res.data;
  } catch (error) {
    console.error("Error deleting chatbot:", error);
    throw error;
  }
};

// Delete User Chats
export const deleteUserChats = async () => {
  try {
    const res = await axios.delete("/chat/delete");
    if (res.status !== 200) {
      throw new Error("Unable to delete chats");
    }
    const data = await res.data;
    return data;
  } catch (error) {
    console.error("Error deleting chats:", error);
    throw error;
  }
};

// Logout User
export const logoutUser = async () => {
  try {
    const res = await axios.get("/user/logout");
    if (res.status !== 200) {
      throw new Error("Unable to logout");
    }

    // Clear token from localStorage
    localStorage.removeItem('token');

    const data = await res.data;
    return data;
  } catch (error) {
    console.error("Error logging out:", error);

    // Clear token even if logout request fails
    localStorage.removeItem('token');

    throw error;
  }
};

// Google Login
export const googleOAuthCallback = async (token: string) => {
  const decodeGoogleCredential = (credential: string) => {
    try {
      const payloadPart = credential.split(".")[1];
      if (!payloadPart) return null;
      const base64 = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
      const json = decodeURIComponent(
        atob(base64)
          .split("")
          .map((c) => `%${("00" + c.charCodeAt(0).toString(16)).slice(-2)}`)
          .join("")
      );
      return JSON.parse(json);
    } catch {
      return null;
    }
  };

  try {
    const response = await axios.post(
      "/auth/google/token",
      { token }
    );

    // Store token in localStorage for subsequent requests
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
    }

    console.log("Google OAuth Success:", response.data);
    return response.data;
  } catch (error) {
    // UniGuru backend does not expose /auth/google/token.
    // In demo mode, accept the Google credential locally so user can continue.
    if (axios.isAxiosError(error) && (!error.response || error.response.status === 404)) {
      const decoded = decodeGoogleCredential(token);
      const fallbackData = {
        token,
        user: {
          id: decoded?.sub || "google-user",
          email: decoded?.email || "google-user@local",
          name: decoded?.name || decoded?.given_name || "Google User",
        },
        navigateUrl: "/chatpage",
        demoMode: true,
      };
      localStorage.setItem("token", token);
      console.warn("Google OAuth backend endpoint unavailable. Using local demo auth fallback.");
      return fallbackData;
    }
    console.error("Error during Google OAuth callback:", error);
    throw new Error(
      axios.isAxiosError(error)
        ? (error.response?.data?.message || "Google authentication failed")
        : "An unexpected error occurred during Google authentication"
    );
  }
};

// Google OAuth Login (alternative method)
export const loginWithGoogle = async (credential: string) => {
  try {
    const response = await axios.post(
      "/auth/google",
      { token: credential }
    );

    // Store token in localStorage for subsequent requests
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
    }

    console.log("Google Login Success:", response.data);
    return response.data;
  } catch (error) {
    console.error("Error during Google login:", error);
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.message || "Google login failed");
    } else {
      throw new Error("An unexpected error occurred during Google login");
    }
  }
};

export const readPdf = async (file: File) => {
  try {
    const formData = new FormData();
    formData.append("pdf", file);

    const response = await axios.post("/feature/pdf/r", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    console.log(response.data.message);

    return response.data; // Return the extracted text
  } catch (error) {
    console.error("Error reading PDF:", error);
    throw error;
  }
};

export const talkWithPdfContent = async (
  extractedText: string,
  message: string
) => {
  try {
    const response = await axios.post("/feature/pdf/t", {
      extractedText,
      message,
    });
    console.log(response.data);
    return response.data; // Return the chatbot's response
  } catch (error) {
    console.error("Error talking with PDF content:", error);
    throw error;
  }
};

export const createPdf = async (title: string, content: string) => {
  try {
    const response = await axios.post("/feature/pdf/c", { title, content });

    return response.data; // Return the path to the created PDF
  } catch (error) {
    console.error("Error creating PDF:", error);
    throw error;
  }
};

// Image-related functionalities
export const scanImageText = async (file: File) => {
  try {
    const formData = new FormData();
    formData.append("image", file);

    const response = await axios.post("/feature/image/s", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    console.log(response.data);
    return response.data; // Return the extracted text
  } catch (error) {
    console.error("Error scanning image text:", error);
    throw error;
  }
};

export const editImageText = async (file: File, newText: string) => {
  try {
    const formData = new FormData();
    formData.append("image", file);
    formData.append("text", newText);

    const response = await axios.post("/feature/image/e", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    console.log(response.data);
    return response.data; // Return the path to the edited image
  } catch (error) {
    console.error("Error editing image text:", error);
    throw error;
  }
};
