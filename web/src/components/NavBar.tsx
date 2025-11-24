'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
  { href: '/', label: 'Home', icon: '🏠' },
  { href: '/schedule', label: 'Schedule', icon: '📅' },
  { href: '/garmin', label: 'Garmin', icon: '⌚' },
  { href: '/history', label: 'History', icon: '📊' },
  { href: '/settings', label: 'Settings', icon: '⚙️' },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-2 py-1 z-50">
      <div className="max-w-2xl mx-auto flex justify-around">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center py-2 px-3 rounded-lg transition-colors ${
                isActive
                  ? 'text-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="text-xs mt-0.5">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
