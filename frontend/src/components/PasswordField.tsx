import { useState } from "react";
import { IconEye, IconEyeOff } from "@tabler/icons-react";

interface PasswordFieldProps {
  id: string;
  label: string;
  autoComplete: string;
  value: string;
  onChange: (value: string) => void;
}

export function PasswordField({
  id,
  label,
  autoComplete,
  value,
  onChange,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="auth-field">
      <label htmlFor={id}>{label}</label>
      <div className="auth-input-wrap">
        <input
          id={id}
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          className="auth-input-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
        >
          {visible ? (
            <IconEyeOff size={18} stroke={1.75} />
          ) : (
            <IconEye size={18} stroke={1.75} />
          )}
        </button>
      </div>
    </div>
  );
}
