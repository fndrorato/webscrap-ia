import { HelmetProvider, Helmet } from "react-helmet-async";

const PageMeta = (_props: {
  title?: string; // Tornar title opcional
  description: string;
}) => (
  <Helmet>
    <title>{import.meta.env.VITE_APP_TITLE}</title> {/* Usar VITE_APP_TITLE como padrão */}
    <meta name="description" content={import.meta.env.VITE_APP_PAGE_DESCRIPTION} />
  </Helmet>
);

export const AppWrapper = ({ children }: { children: React.ReactNode }) => (
  <HelmetProvider>{children}</HelmetProvider>
);

export default PageMeta;
