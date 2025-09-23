import SignInForm from "../../components/auth/SignInForm";
import AuthLayout from "./AuthPageLayout";
import PageMeta from "../../components/common/PageMeta";

interface SignInProps {
  onLoginSuccess: () => void;
}

export default function SignIn({ onLoginSuccess }: SignInProps) {
  return (
    <>
      <PageMeta
        description="This is React.js SignIn Tables Dashboard page for TailAdmin - React.js Tailwind CSS Admin Dashboard Template"
      />
      <AuthLayout>
        <SignInForm onLoginSuccess={onLoginSuccess} />
      </AuthLayout>
    </>
  );
}
