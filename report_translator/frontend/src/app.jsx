import { useState } from "preact/hooks";
import { Header } from "./components/Header.jsx";
import { UploadView } from "./components/UploadView.jsx";
import { EditorView } from "./components/EditorView.jsx";
import "./styles/components.css";

export function App() {
  const [session, setSession] = useState(null);
  const [files, setFiles] = useState([]);
  const [editing, setEditing] = useState(null);
  return (
    <div class="app">
      <Header />
      {editing
        ? <EditorView session={session} file={editing} onBack={() => setEditing(null)} />
        : <UploadView session={session} files={files} setSession={setSession}
            setFiles={setFiles} onOpen={setEditing} />}
    </div>
  );
}
