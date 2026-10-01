import { useEffect, useRef, useState } from "react";
import "./App.css";

function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);

  // PDF upload states
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");

  // Documents
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);

  // History
  const [history, setHistory] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);

  const historyPanelRef = useRef(null);

  // --------------------------------------------------
  // ASK QUESTION
  // --------------------------------------------------

  const askQuestion = async () => {
    if (!question.trim()) {
      return;
    }

    const currentQuestion = question.trim();

    console.log("1. ASK BUTTON CLICKED");

    setLoading(true);
    setAnswer("");
    setSources([]);

    try {
      console.log("2. Sending request to FastAPI...");

      const response = await fetch(
        "http://127.0.0.1:8000/api/chat",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: currentQuestion,
          }),
        }
      );

      console.log("3. Response received");

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);

        throw new Error(
          errorData?.detail ||
          `Server error: ${response.status}`
        );
      }

      const data = await response.json();

      console.log("4. Response data:", data);

      setAnswer(data.answer);
      setSources(data.sources || []);

      // Add question and answer to history
      const historyItem = {
        id: Date.now(),
        question: currentQuestion,
        answer: data.answer,
        sources: data.sources || [],
      };

      setHistory((previousHistory) => [
        historyItem,
        ...previousHistory,
      ]);

      // Clear input after successful question
      setQuestion("");

    } catch (error) {
      console.error("5. ERROR:", error);

      setAnswer(
        error.message ||
        "Something went wrong. Please try again."
      );

    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // HANDLE ENTER KEY
  // --------------------------------------------------

  const handleQuestionKeyDown = (event) => {
    if (event.key === "Enter" && !loading) {
      askQuestion();
    }
  };

  // --------------------------------------------------
  // PDF FILE SELECTION
  // --------------------------------------------------

  const handleFileChange = (event) => {
    const file = event.target.files[0];

    if (!file) {
      return;
    }

    if (file.type !== "application/pdf") {
      setUploadMessage("Please select a PDF file.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setUploadMessage("");
  };

  // --------------------------------------------------
  // UPLOAD PDF
  // --------------------------------------------------

  const uploadPDF = async () => {
    if (!selectedFile) {
      setUploadMessage("Please select a PDF file first.");
      return;
    }

    console.log("1. UPLOAD BUTTON CLICKED");

    setUploading(true);
    setUploadMessage("");

    try {
      const formData = new FormData();

      formData.append("file", selectedFile);

      console.log("2. Sending PDF to FastAPI...");

      const response = await fetch(
        "http://127.0.0.1:8000/api/documents/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      console.log("3. Upload response received");

      const data = await response.json();

      console.log("4. Upload response:", data);

      if (!response.ok) {
        throw new Error(
          data.detail || "Upload failed"
        );
      }

      if (data.status === "indexed") {
        setUploadMessage(
          `✓ ${data.filename} uploaded successfully. ${data.chunks_created} chunks created.`
        );

        await loadDocuments();

      } else if (data.status === "already_indexed") {
        setUploadMessage(
          `✓ ${data.filename} is already indexed.`
        );

        await loadDocuments();

      } else {
        setUploadMessage(
          "PDF uploaded successfully."
        );
      }

      setSelectedFile(null);

      const input = document.getElementById("pdf-input");

      if (input) {
        input.value = "";
      }

    } catch (error) {
      console.error("5. UPLOAD ERROR:", error);

      setUploadMessage(
        `Upload failed: ${error.message}`
      );

    } finally {
      setUploading(false);
    }
  };

  // --------------------------------------------------
  // LOAD DOCUMENTS
  // --------------------------------------------------

  const loadDocuments = async () => {
    setDocumentsLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/documents"
      );

      if (!response.ok) {
        throw new Error(
          `Server error: ${response.status}`
        );
      }

      const data = await response.json();

      console.log("Documents:", data);

      setDocuments(data.documents || []);

    } catch (error) {
      console.error(
        "DOCUMENT ERROR:",
        error
      );

    } finally {
      setDocumentsLoading(false);
    }
  };

  // --------------------------------------------------
  // DELETE DOCUMENT
  // --------------------------------------------------

  const deleteDocument = async (filename) => {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/documents/${encodeURIComponent(
          filename
        )}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error(
          `Server error: ${response.status}`
        );
      }

      const data = await response.json();

      console.log(
        "Delete response:",
        data
      );

      if (data.status === "deleted") {
        setUploadMessage(
          `✓ ${filename} deleted successfully.`
        );

      } else if (data.status === "not_found") {
        setUploadMessage(
          `Document ${filename} was not found.`
        );
      }

      await loadDocuments();

    } catch (error) {
      console.error(
        "DELETE ERROR:",
        error
      );

      setUploadMessage(
        `Delete failed: ${error.message}`
      );
    }
  };

  // --------------------------------------------------
  // SELECT HISTORY ITEM
  // --------------------------------------------------

  const selectHistoryItem = (item) => {
    setQuestion(item.question);
    setAnswer(item.answer);
    setSources(item.sources || []);

    // Close history panel
    setHistoryOpen(false);
  };

  // --------------------------------------------------
  // CLEAR HISTORY
  // --------------------------------------------------

  const clearHistory = () => {
    setHistory([]);
  };

  // --------------------------------------------------
  // CLOSE HISTORY WHEN CLICKING OUTSIDE
  // --------------------------------------------------

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        historyOpen &&
        historyPanelRef.current &&
        !historyPanelRef.current.contains(
          event.target
        )
      ) {
        setHistoryOpen(false);
      }
    };

    document.addEventListener(
      "mousedown",
      handleClickOutside
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClickOutside
      );
    };
  }, [historyOpen]);

  // --------------------------------------------------
  // LOAD DOCUMENTS ON START
  // --------------------------------------------------

  useEffect(() => {
    loadDocuments();
  }, []);

  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <div className="app">

      {/* HEADER */}

      <header className="header">

        <div>
          <h1>AI Knowledge Assistant</h1>

          <p>
            Ask questions about your uploaded documents
          </p>
        </div>

        {/* HISTORY BUTTON */}

        <button
          className="history-button"
          onClick={() =>
            setHistoryOpen(true)
          }
        >
          🕘 History
        </button>

      </header>


      {/* HISTORY PANEL */}

      {historyOpen && (
        <div className="history-overlay">

          <div
            className="history-panel"
            ref={historyPanelRef}
          >

            {/* HISTORY HEADER */}

            <div className="history-header">

              <h2>Chat History</h2>

              <button
                className="history-close"
                onClick={() =>
                  setHistoryOpen(false)
                }
              >
                ×
              </button>

            </div>


            {/* HISTORY CONTENT */}

            {history.length === 0 ? (

              <div className="empty-history">
                <p>No questions asked yet.</p>
              </div>

            ) : (

              <div className="history-list">

                {history.map((item) => (

                  <div
                    className="history-item"
                    key={item.id}
                    onClick={() =>
                      selectHistoryItem(item)
                    }
                  >

                    <div className="history-question">
                      <strong>
                        {item.question}
                      </strong>
                    </div>

                    <div className="history-answer">
                      {item.answer}
                    </div>

                  </div>

                ))}

              </div>

            )}


            {/* CLEAR HISTORY */}

            {history.length > 0 && (
              <button
                className="clear-history-button"
                onClick={clearHistory}
              >
                Clear History
              </button>
            )}

          </div>

        </div>
      )}


      {/* MAIN */}

      <main className="main">

        <section className="chat-container">


          {/* PDF UPLOAD */}

          <div className="upload-section">

            <h2>
              Upload Knowledge Document
            </h2>

            <p>
              Upload a PDF document to add it
              to the knowledge base.
            </p>

            <input
              id="pdf-input"
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              disabled={uploading}
            />

            {selectedFile && (
              <p>
                Selected file:{" "}
                <strong>
                  {selectedFile.name}
                </strong>
              </p>
            )}

            <button
              onClick={uploadPDF}
              disabled={
                uploading ||
                !selectedFile
              }
            >
              {uploading
                ? "⏳ Uploading..."
                : "Upload PDF"}
            </button>

            {uploadMessage && (
              <p className="upload-message">
                {uploadMessage}
              </p>
            )}

          </div>


          {/* DOCUMENTS */}

          <div className="documents-section">

            <h2>
              Uploaded Documents
            </h2>

            {documentsLoading ? (

              <p>
                Loading documents...
              </p>

            ) : documents.length === 0 ? (

              <p>
                No documents uploaded yet.
              </p>

            ) : (

              <div className="document-list">

                {documents.map(
                  (document) => (

                    <div
                      className="document-item"
                      key={document.filename}
                    >

                      <div>

                        <strong>
                          📄{" "}
                          {document.filename}
                        </strong>

                        <p>
                          {document.chunks} chunks
                        </p>

                      </div>

                      <button
                        onClick={() =>
                          deleteDocument(
                            document.filename
                          )
                        }
                        disabled={uploading}
                      >
                        Delete
                      </button>

                    </div>

                  )
                )}

              </div>

            )}

          </div>


          {/* WELCOME */}

          <div className="welcome">

            <h2>
              Welcome 👋
            </h2>

            <p>
              Ask a question and the AI will
              find relevant information from
              your documents.
            </p>

          </div>


          {/* CHAT INPUT */}

          <div className="input-area">

            <input
              type="text"
              placeholder="Ask something about your documents..."
              value={question}
              onChange={(event) =>
                setQuestion(event.target.value)
              }
              onKeyDown={
                handleQuestionKeyDown
              }
              disabled={loading}
            />

            <button
              onClick={askQuestion}
              disabled={
                loading ||
                !question.trim()
              }
              className={
                loading
                  ? "loading-button"
                  : ""
              }
            >
              {loading
                ? "⏳ Thinking..."
                : "Ask"}
            </button>

          </div>


          {/* ANSWER */}

          {answer && (

            <div className="answer-box">

              <h3>
                Answer
              </h3>

              <p>
                {answer}
              </p>


              {/* SOURCES */}

              {sources.length > 0 && (

                <div className="sources-section">

                  <h3>
                    Sources
                  </h3>

                  {sources.map(
                    (source, index) => (

                      <div
                        className="source-item"
                        key={`${source.filename}-${source.chunk_id}-${index}`}
                      >

                        <strong>
                          📄{" "}
                          {source.filename}
                        </strong>

                        <p>
                          Chunk:{" "}
                          {source.chunk_id}
                        </p>

                        <p>
                          {source.text}
                        </p>

                      </div>

                    )
                  )}

                </div>

              )}

            </div>

          )}

        </section>

      </main>

    </div>
  );
}

export default App;