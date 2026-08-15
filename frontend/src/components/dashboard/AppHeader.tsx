import { IconBell } from "@tabler/icons-react";

interface AppHeaderProps {
  firstName: string;
  lastName: string;
  onSignOut: () => void;
  onNotificationsClick: () => void;
}

export function AppHeader({ firstName, lastName, onSignOut, onNotificationsClick }: AppHeaderProps) {
  const initials = `${firstName[0] ?? ""}${lastName[0] ?? ""}`.toUpperCase();

  return (
    <header className="app-header">
      <p className="wordmark app-header-wordmark">koala</p>
      <div className="app-header-actions">
        <button
          type="button"
          className="app-header-icon-btn"
          aria-label="Notifications"
          onClick={onNotificationsClick}
        >
          <IconBell size={20} stroke={1.75} />
        </button>
        <button
          type="button"
          className="app-header-avatar"
          onClick={onSignOut}
          aria-label="Sign out"
          title="Sign out"
        >
          {initials || "?"}
        </button>
      </div>
    </header>
  );
}
