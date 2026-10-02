import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import AuthCard from "./AuthCard";
import AuthInput from "./AuthInput";
import AuthButton from "./AuthButton";
import { signupUser } from "../helpers/api-communicator";

type FormData = {
  name: string;
  email: string;
  password: string;
};



interface FieldErrors {
  name?: string;
  email?: string;
  password?: string;
  general?: string;
}

const Signupbox: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<FormData>({
    name: "",
    email: "",
    password: "",
  });

  const [errors, setErrors] = useState<FieldErrors>({});
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    // Clear specific field error when user starts typing
    if (errors[name as keyof FieldErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: FieldErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = "Name is required";
    } else if (formData.name.trim().length < 2) {
      newErrors.name = "Name must be at least 2 characters";
    }

    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Please enter a valid email address";
    }

    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      toast.loading("Creating your account...", { id: "signup" });

      const response = await signupUser(formData.name, formData.email, formData.password);

      if (response.success) {
        if (response.requires_email_verification) {
          toast.success(
            "Account created. Please verify your email from the inbox, then login.",
            { id: "signup", duration: 4500 }
          );
        } else {
          toast.success("Account created successfully! Please login to continue.", { id: "signup" });
        }
        // Reset form
        setFormData({ name: "", email: "", password: "" });
        // Redirect to login page after a short delay
        setTimeout(() => {
          navigate("/login");
        }, 1500);
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "Signup failed. Please try again.";

      // Check if error is field-specific
      if (errorMessage.toLowerCase().includes('email')) {
        setErrors({ email: errorMessage });
      } else if (errorMessage.toLowerCase().includes('password')) {
        setErrors({ password: errorMessage });
      } else if (errorMessage.toLowerCase().includes('name')) {
        setErrors({ name: errorMessage });
      } else {
        setErrors({ general: errorMessage });
      }

      toast.error(errorMessage, { id: "signup" });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthCard title="Create Account">
      <form onSubmit={handleSubmit}>
        <AuthInput
          type="text"
          name="name"
          placeholder="Full Name"
          value={formData.name}
          onChange={handleChange}
          required
          autoComplete="name"
          label="Name"
          error={errors.name}
        />

        <AuthInput
          type="email"
          name="email"
          placeholder="Email Address"
          value={formData.email}
          onChange={handleChange}
          required
          autoComplete="email"
          label="Email"
          error={errors.email}
        />

        <AuthInput
          type="password"
          name="password"
          placeholder="Password"
          value={formData.password}
          onChange={handleChange}
          required
          autoComplete="new-password"
          label="Password"
          error={errors.password}
        />

        {/* General error message */}
        {errors.general && (
          <p className="text-red-400 text-sm font-medium mt-4 font-poppins">
            {errors.general}
          </p>
        )}

        <AuthButton
          type="submit"
          loading={isLoading}
          disabled={isLoading}
          variant="primary"
        >
          {isLoading ? "Creating Account..." : "Sign Up"}
        </AuthButton>
      </form>
    </AuthCard>
  );
};

export default Signupbox;
