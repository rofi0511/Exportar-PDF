import { useEffect, useState } from "react";
import { FaUpload, FaCheckCircle } from "react-icons/fa";
import { motion } from "framer-motion";

const backendURL =
  process.env.NODE_ENV === "development"
    ? "http://localhost:5001"  // Para pruebas
    : "http://192.168.137.54:5000"; // Para producción

function App() {
  const [files, setFiles] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [fileType, setFileType] = useState("excel");
  const [showDownloadOptions, setShowDownloadOptions] = useState(false)

  const handleUpload = async () => {
    if (files.length === 0) return;
    setIsProcessing(true);
    setUploadSuccess(false);
    setShowDownloadOptions(false);
    
    const formData = new FormData();
    files.forEach(file => formData.append("files", file));

    try {
      const response = await fetch(`${backendURL}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      console.log("Respuesta del servidor", data)

     if (data.processed) {
      setUploadSuccess(true)
      setShowDownloadOptions(true);
     }
    } catch (error) {
      console.error("Error en la subida:", error);
    }
    setIsProcessing(false);
  };

  const handleGenerateFile = async () => {
    try {
      console.log("Generando archivo en formato:", fileType)

      const response = await fetch(`${backendURL}/generate?file_type=${fileType}`)
      const data = await response.json()
      console.log("Archivo generado:", data)

      if (data.file_path) {
        const downloadUrl = `${backendURL}/${data.file_path}`
        setDownloadUrl(downloadUrl)
      } else {
        console.error("Error: No se pudo generar el archivo.")
      }
    } catch (error) {
      console.error("Error al generar el archivo:", error)
    }
  }

  useEffect(() => {
    if (uploadSuccess) {
      handleGenerateFile();
    }
  }, [uploadSuccess])

  const handleFileChange = (event) => {
    setFiles([...event.target.files]);
  };

  const handleDragOver = (event) => {
    event.preventDefault()
  }

  const handleDrop = (event) => {
    event.preventDefault()
    const droppedFiles = Array.from(event.dataTransfer.files);
    if (droppedFiles.length) {
      setFiles(droppedFiles);
    }
  }

  return (
    <motion.div
      className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 text-white p-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1 }}
    >
      <motion.div
        className="bg-white text-gray-900 p-10 rounded-xl shadow-lg w-full max-w-xl text-center flex flex-col items-center"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5 }}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <h1 className="text-3xl font-bold mb-3">Extraer Estados de Cuenta</h1>
        <p className="text-gray-600 mb-5">Sube tu PDFs y obtén los datos en un solo archivo Excel.</p>

        <motion.label
          className="cursor-pointer bg-blue-500 px-6 py-4 rounded-lg text-white font-semibold text-lg flex items-center justify-center gap-3 shadow-md w-full hover:bg-blue-600"
          whileHover={{ scale: 1.05 }}
        >
          <input
            type="file"
            className="hidden"
            multiple
            onChange={handleFileChange}
          />
          <FaUpload /> Seleccionar Archivos PDF
        </motion.label>

        
        <motion.div
          className="border-2 border-dashed border-gray-400 p-6 rounded-lg w-full flex flex-col items-center justify-center cursor-pointer bg-gray-100 hover:bg-gray-200 mt-4"
          whileHover={{ scale: 1.05 }}
        >
          <FaUpload className="text-gray-500 text-3xl mb-2" />
          <p className="text-gray-600">Arrastra y suelta aquí tu archivos PDF</p>
        </motion.div>

        {files.length > 0 && (
          <motion.div
            className="flex flex-col items-center mt-4 bg-gray-200 p-4 rounded-lg shadow-md w-full"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            {files.map((file, index) => (
              <p key={index} className="text-gray-900">{file.name}</p>
            ))}
          </motion.div>
        )}

        {files.length > 0 && (

          <motion.button
            className="mt-6 bg-green-500 px-6 py-3 rounded-lg hover:bg-green-700 text-lg font-semibold disabled:opacity-50 flex items-center gap-2 w-full justify-center shadow-md"
            onClick={handleUpload}
            disabled={isProcessing}
            whileTap={{ scale: 0.95 }}
          >
            {isProcessing ? "⌛ Procesando..." : "🚀 Subir Archivos"}
          </motion.button>
        )}

        {uploadSuccess && (
          <motion.div
            className="mt-4 flex items-center gap-2 bg-green-100 text-green-700 px-4 py-2 rounded-lg shadow-md"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <FaCheckCircle className="text-green-500" /> Archivos procesados con éxito
          </motion.div>
        )}

        {/*showDownloadOptions && (
          <div className="mt-4 flex flex-col items-center">
            <label className="text-gray-900 font-semibold mb-2">Selecciona el tipo de archivo:</label>
            <select className="mb-4 p-2 border rounded-lg" value={fileType} onChange={(e) => setFileType(e.target.value)}>
              <option value="excel">Excel (.xlsx)</option>
              <option value="csv">CSV (.csv)</option>
              <option value="txt">Texto (.txt)</option>
            </select>

            <motion.button
              className="mt-6 bg-blue-500 px-6 py-3 rounded-lg hover:bg-blue-700 text-lg font-semibold w-full shadow-md"
              onClick={handleGenerateFile}
              whileTap={{ scale: 0.95 }}
            >
              🚀 Generar Archivo
            </motion.button>

          </div>
        )*/}

        {downloadUrl && (
          <a href={downloadUrl} download>
            <button>Descargar Archivo</button>
          </a>
        )}
          
      </motion.div>
    </motion.div>
  );
}

export default App;