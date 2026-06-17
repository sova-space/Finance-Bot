interface ErrorStateProps {
  message: string;
}

export function ErrorState({ message }: ErrorStateProps) {
  return <p className="error-msg">Failed to load: {message}</p>;
}
