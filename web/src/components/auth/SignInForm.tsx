import { useState } from "react";
import { Link, useNavigate } from "react-router";
import axios, { loginEndpoint } from "../../api/axios";
import { EyeCloseIcon, EyeIcon } from "../../icons";
import Label from "../form/Label";
import Input from "../form/input/InputField";
import Checkbox from "../form/input/Checkbox";
import Button from "../ui/button/Button";
import { useTranslation } from 'react-i18next';
import { useAuth } from "../../context/AuthContext";


interface SignInFormProps {
  onLoginSuccess?: () => void;
}

export default function SignInForm({ onLoginSuccess }: SignInFormProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isChecked, setIsChecked] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(loginEndpoint, {
        username: email,
        password: password,
      });

      const { access, refresh, first_name, last_name, user_id, phone, photo, permissions } = response.data;
      login(
        {
          firstName: first_name,
          lastName: last_name,
          email: email,
          userId: user_id,
          permissions: permissions,
          phone: phone,
          photo: photo
        },
        access,
        refresh
      );

      if (onLoginSuccess) {
        onLoginSuccess();
      }
      navigate('/'); // Redirect to dashboard
    } catch (err) {
      console.error('Login failed:', err);
      setError('Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="flex flex-col flex-1">

      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
        <div>
          <div className="mb-5 sm:mb-8">
            <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
              {t('signIn')}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('signInDescription')}
            </p>
          </div>
          <div>
            <form onSubmit={handleSubmit}>
              <div className="space-y-6">
                <div>
                  <Label>
                    {t('email')} <span className="text-error-500">*</span>{" "}
                  </Label>
                  <Input
                    placeholder="usuario"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    type="text"
                    required
                  />
                </div>
                <div>
                  <Label>
                    {t('password')} <span className="text-error-500">*</span>{" "}
                  </Label>
                  <div className="relative">
                    <Input
                      type={showPassword ? "text" : "password"}
                      placeholder={t('enterYourPassword')}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                    <span
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                    >
                      {showPassword ? (
                        <EyeIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                      ) : (
                        <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                      )}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Checkbox checked={isChecked} onChange={setIsChecked} />
                    <span className="block font-normal text-gray-700 text-theme-sm dark:text-gray-400">
                      {t('rememberMe')}
                    </span>
                  </div>
                  <Link
                    to="/reset-password"
                    className="text-sm text-brand-500 hover:text-brand-600 dark:text-brand-400"
                  >
                    {t('forgotPassword')}
                  </Link>
                </div>
                {error && <p className="text-error-500 text-sm">{error}</p>}
                <div>
                  <Button className="w-full" size="sm" type="submit" disabled={loading}>
                    {loading ? 'Signing In...' : t('signIn')}
                  </Button>
                </div>
              </div>
            </form>

          </div>
        </div>
      </div>
    </div>
  );
}
