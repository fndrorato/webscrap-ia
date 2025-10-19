// import { SidebarProvider, useSidebar } from "../context/SidebarContext";
import { Outlet } from "react-router";
import AppHeader from "./AppHeader";
// import Backdrop from "./Backdrop";
// import AppSidebar from "./AppSidebar";

const LayoutContent: React.FC = () => {
  // const { isExpanded, isHovered, isMobileOpen } = useSidebar();

  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader />
      {/* <div>
        <AppSidebar />
        <Backdrop />
      </div> */}
      <div
        className={`flex-1 transition-all duration-300 ease-in-out `}
      >
        {/* <AppHeader /> */}
        {/* <div className="p-4 mx-auto max-w-(--breakpoint-2xl) md:p-6 flex-1 flex flex-col h-full"> */}
        <div className="p-4 md:p-6 flex-1 flex flex-col">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

const AppLayout: React.FC = () => {
  return (
    // <SidebarProvider>
      <LayoutContent />
    // </SidebarProvider>
  );
};

export default AppLayout;
