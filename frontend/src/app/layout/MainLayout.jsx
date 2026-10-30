import { Outlet } from 'react-router-dom'

import SideNav from './SideNav'
import TopBar from './TopBar'

/** Khung chung: sidebar cố định + topbar + nội dung trang được định tuyến. */
export default function MainLayout() {
  return (
    <div className="shell">
      <SideNav />
      <div className="shell-main">
        <TopBar />
        <main className="shell-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
