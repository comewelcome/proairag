import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileText, Upload, Trash2, File, FileSpreadsheet, FileCode, ChevronDown, ChevronUp, Search } from 'lucide-react';
import { api } from '../lib/api';
import { EmptyState } from '../components/common/EmptyState';
import { toast } from 'sonner';
import type { DocumentItem, Department } from '../types';

const fileIcon = (contentType: string) => {
  if (contentType.includes('pdf')) return <File className="text-red-400" size={20} />;
  if (contentType.includes('word') || contentType.includes('docx')) return <File className="text-blue-400" size={20} />;
  if (contentType.includes('csv') || contentType.includes('spreadsheet')) return <FileSpreadsheet className="text-green-400" size={20} />;
  if (contentType.includes('text') || contentType.includes('markdown')) return <FileCode className="text-yellow-400" size={20} />;
  return <FileText className="text-text-muted" size={20} />;
};

export function Documents() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [search, setSearch] = useState('');
  const [deptDropdown, setDeptDropdown] = useState(false);

  const loadDocs = async () => {
    try {
      const params = selectedDept ? { department_id: selectedDept } : {};
      const { data } = await api.get<DocumentItem[]>('/documents/', { params });
      setDocuments(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les documents');
    }
  };

  const loadDepts = async () => {
    try {
      const { data } = await api.get<Department[]>('/departments/');
      setDepartments(Array.isArray(data) ? data : []);
    } catch { /* ignore */ }
  };

  useEffect(() => { loadDocs(); loadDepts(); }, []);
  useEffect(() => { loadDocs(); }, [selectedDept]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (uploading) return;
    setUploading(true);
    setUploadProgress(0);

    for (let i = 0; i < acceptedFiles.length; i++) {
      const file = acceptedFiles[i];
      const progress = Math.round(((i + 1) / acceptedFiles.length) * 100);
      setUploadProgress(progress);

      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', file.name.replace(/\.[^.]+$/, ''));
        if (selectedDept) formData.append('department_id', selectedDept);

        await api.post('/documents/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        toast.success(`${file.name} importe avec succes`);
      } catch {
        toast.error(`Echec de l'import de ${file.name}`);
      }
    }

    setUploading(false);
    setUploadProgress(0);
    loadDocs();
  }, [uploading, selectedDept]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt', '.md'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/csv': ['.csv'],
    },
    disabled: uploading,
  });

  const handleDelete = async (id: string) => {
    if (!confirm('Supprimer ce document ?')) return;
    try {
      await api.delete(`/documents/${id}`);
      toast.success('Document supprime');
      loadDocs();
    } catch {
      toast.error('Erreur lors de la suppression');
    }
  };

  const filtered = documents.filter(d =>
    d.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-text">Documents</h2>
          <p className="text-text-muted text-sm mt-1">Importez et gepez vos documents</p>
        </div>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`card mb-6 text-center cursor-pointer transition-all border-2 border-dashed ${
          isDragActive ? 'border-accent bg-accent/5' : 'hover:border-accent/50'
        } ${uploading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="py-8">
            <div className="w-full bg-bg-secondary rounded-full h-2 mb-3">
              <div className="bg-accent h-2 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
            </div>
            <p className="text-text-muted text-sm">Import en cours... {uploadProgress}%</p>
          </div>
        ) : isDragActive ? (
          <div className="py-8">
            <Upload className="text-accent mx-auto mb-2" size={32} />
            <p className="text-text">Deposez vos fichiers ici</p>
          </div>
        ) : (
          <div className="py-8">
            <Upload className="text-text-muted mx-auto mb-2" size={32} />
            <p className="text-text font-medium">Glissez vos fichiers ici</p>
            <p className="text-text-muted text-sm mt-1">ou cliquez pour selectionner</p>
            <p className="text-text-muted/50 text-xs mt-2">PDF, TXT, DOCX, CSV - max 50MB</p>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" size={16} />
          <input
            className="input-base pl-9"
            placeholder="Rechercher un document..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="relative">
          <button
            onClick={() => setDeptDropdown(!deptDropdown)}
            className="btn-secondary flex items-center gap-2"
          >
            {departments.find(d => d.id === selectedDept)?.name || 'Tous les services'}
            {deptDropdown ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {deptDropdown && (
            <div className="absolute right-0 top-full mt-1 bg-bg-card border border-border rounded-lg shadow-xl z-10 min-w-[200px]">
              <button
                onClick={() => { setSelectedDept(''); setDeptDropdown(false); }}
                className="w-full text-left px-3 py-2 text-sm text-text hover:bg-bg-card/80 rounded-t-lg"
              >
                Tous les services
              </button>
              {departments.map(d => (
                <button
                  key={d.id}
                  onClick={() => { setSelectedDept(d.id); setDeptDropdown(false); }}
                  className="w-full text-left px-3 py-2 text-sm text-text hover:bg-bg-card/80"
                >
                  {d.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Document list */}
      {filtered.length === 0 ? (
        <EmptyState
          icon={<FileText size={48} />}
          title="Aucun document"
          description="Importez des fichiers PDF, TXT, DOCX ou CSV"
        />
      ) : (
        <div className="space-y-2">
          {filtered.map((doc) => (
            <div key={doc.id} className="card flex items-center justify-between">
              <div className="flex items-center gap-3">
                {fileIcon(doc.content_type)}
                <div>
                  <p className="font-medium text-text">{doc.title}</p>
                  <p className="text-text-muted text-xs mt-0.5">
                    {doc.content_type} {doc.source ? `• ${doc.source}` : ''}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {doc.department_id && (
                  <span className="text-xs text-text-muted bg-bg-secondary px-2 py-1 rounded-md">
                    {departments.find(d => d.id === doc.department_id)?.name || 'Service'}
                  </span>
                )}
                <button onClick={() => handleDelete(doc.id)} className="btn-danger text-sm px-2 py-1">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
