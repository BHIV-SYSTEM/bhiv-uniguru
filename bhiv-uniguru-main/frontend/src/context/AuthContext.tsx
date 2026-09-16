import {
  ReactNode,
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";
import { useParams } from "react-router-dom";
import {
  checkAuthStatus,
  loginUser,
  logoutUser,
  signupUser,
  fetchUserGurus,
  googleOAuthCallback,
  deleteGuru,
} from "../helpers/api-communicator.tsx";
import { NavigateFunction } from "react-router-dom";


import mongoose from "mongoose";

// Define the structure of a message
export interface IMessage {
    metadata: { retrieved_chunks: never[]; };
    sender: 'user' | 'guru';
    content: string;
    timestamp: Date;
}

// Define the structure of the Chat schema
export interface IChat {
    _id: mongoose.Types.ObjectId; // MongoDB ObjectId
    user: mongoose.Types.ObjectId; // Refers to a User
    chatbot: mongoose.Types.ObjectId; // Refers to a Chatbot
    title:string;
    messages: IMessage[]; // Array of messages
    createdAt: Date;
    updatedAt: Date;
}



type User = {
  id: string;
  name: string;
  email: string;
};

type Guru = {
  name: string;
  description: string;
  subject: string;
  id: string;
  userid: string;
};

type UserAuth = {
  isLoggedIn: boolean;
  user: User | null;
  selectedGuru: Guru | null;
  isAuthLoading: boolean;
  login: (email: string, password: string) => Promise<{ navigateUrl?: string }>;
  signup: (
    name: string,
    email: string,
    password: string
  ) => Promise<{ navigateUrl?: string }>;
  logout: (navigate: NavigateFunction) => Promise<void>; // Accepts navigate as a parameter
  googleLogin: (token: string) => Promise<{ navigateUrl?: string }>;
  setSelectedGuru: (guru: Guru | null) => void;
  addGuru: (guru: Guru) => void;
  removeGuru: (guruId: string) => void;
  setGurus: (update: (prevGurus: Guru[]) => Guru[]) => void;
  gurus: Guru[];
};

const AuthContext = createContext<UserAuth | null>(null);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const { guruName } = useParams<{ guruName: string }>();
  const [user, setUser] = useState<User | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [gurus, setGurus] = useState<Guru[]>([]);
  const [selectedGuru, setSelectedGuru] = useState<Guru | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars

  useEffect(() => {
    const checkStatus = async () => {
      try {
        setIsAuthLoading(true);
        const data = await checkAuthStatus();
        if (data && data.authenticated) {
          setUser({ id: data.id, email: data.email, name: data.name });
          setIsLoggedIn(true);

          // Auto-load gurus
          const userGurus = await fetchUserGurus();
          setGurus(userGurus || []);

          // Auto-select guru based on URL params or first available
          const guruFromParams = guruName && userGurus
            ? userGurus.find((guru: { name: string }) => guru.name === guruName)
            : userGurus?.[0];
          setSelectedGuru(guruFromParams || null);
        } else {
          // User is not authenticated
          setUser(null);
          setIsLoggedIn(false);
          setGurus([]);
          setSelectedGuru(null);
        }
      } catch (error) {
        console.error("Error checking auth status:", error);
        // On error, assume user is not authenticated
        setUser(null);
        setIsLoggedIn(false);
        setGurus([]);
        setSelectedGuru(null);
      } finally {
        setIsAuthLoading(false);
      }
    };
    checkStatus();
  }, [guruName]);

  const login = async (
    email: string,
    password: string
  ): Promise<{ navigateUrl?: string }> => {
    try {
      const data = await loginUser(email, password);
      if (data) {
        setUser({ id: data.id, email: data.email, name: data.name });
        setIsLoggedIn(true);
        localStorage.setItem("token", data.token);
        const userGurus = await fetchUserGurus();
        setGurus(userGurus || []);

        const guruFromParams = guruName && userGurus
          ? userGurus.find((guru: { name: string }) => guru.name === guruName)
          : userGurus?.[0];
        setSelectedGuru(guruFromParams || null);

        return { navigateUrl: data.navigateUrl || "/default-url" };
      }
      return {};
    } catch (error) {
      console.error("Error during login:", error);
      const message = error instanceof Error ? error.message : "Login failed. Please try again.";
      throw new Error(message);
    }
  };

  const signup = async (
    name: string,
    email: string,
    password: string
  ): Promise<{ navigateUrl?: string }> => {
    try {
      const data = await signupUser(name, email, password);
      console.log("The Data is "+data);
      if (data) {
        setUser({ id: data.id, email: data.email, name: data.name });
        setIsLoggedIn(true);
        localStorage.setItem("token", data.token);
        const userGurus = await fetchUserGurus();
        setGurus(userGurus || []);

        const guruFromParams = guruName && userGurus
          ? userGurus.find((guru: { name: string }) => guru.name === guruName)
          : userGurus?.[0];
        setSelectedGuru(guruFromParams || null);

        return { navigateUrl: data.navigateUrl };
      }
      return {};
    } catch (error) {
      console.error("Error during signup:", error);
      const message = error instanceof Error ? error.message : "Signup failed. Please try again.";
      throw new Error(message);
    }
  };

  const googleLogin = async (
    token: string
  ): Promise<{ navigateUrl?: string }> => {
    try {
      const data = await googleOAuthCallback(token);
      if (data) {
        setUser({
          id: data.user.id,
          email: data.user.email,
          name: data.user.name,
        });
        setIsLoggedIn(true);
        localStorage.setItem("token", data.token);
        let userGurus: Guru[] = [];
        try {
          userGurus = (await fetchUserGurus()) || [];
        } catch (guruError) {
          // Do not fail Google login if optional guru list endpoint is unavailable.
          console.warn("fetchUserGurus failed after Google login, continuing with empty list", guruError);
        }
        setGurus(userGurus || []);

        const guruFromParams = guruName && userGurus
          ? userGurus.find((guru: { name: string }) => guru.name === guruName)
          : userGurus?.[0];
        setSelectedGuru(guruFromParams || null);

        return { navigateUrl: data.navigateUrl };
      }
      return {};
    } catch (error) {
      console.error("Error during Google login:", error);
      const message = error instanceof Error ? error.message : "Google login failed. Please try again.";
      throw new Error(message);
    }
  };


  const logout = async (navigate: NavigateFunction) => {
    try {
      await logoutUser(); // Backend API call to logout
      setUser(null);
      setGurus([]);
      setSelectedGuru(null);
      setIsLoggedIn(false);
      navigate("/login"); // Now you can use navigate here
    } catch (error) {
      console.error("Error during logout:", error);
    }
  };

  const addGuru = (newGuru: Guru) => {
    setGurus((prevGurus) => {
      const updatedGurus = [...prevGurus, newGuru];
      if (updatedGurus.length === 1) {
        setSelectedGuru(newGuru);
      }
      return updatedGurus;
    });
  };

  const removeGuru = async (guruId: string) => {
    try {
      await deleteGuru(guruId);
      setGurus((prevGurus) => {
        const updatedGurus = prevGurus.filter((guru) => guru.id !== guruId);
        if (selectedGuru?.id === guruId) {
          setSelectedGuru(updatedGurus[0] || null);
        }
        return updatedGurus;
      });
    } catch (error) {
      console.error("Error deleting guru:", error);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoggedIn,
        isAuthLoading,
        selectedGuru,
        setSelectedGuru,
        addGuru,
        removeGuru,
        setGurus: (update) => setGurus((prev) => update(prev)),
        login,
        logout,
        signup,
        googleLogin,
        gurus,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
