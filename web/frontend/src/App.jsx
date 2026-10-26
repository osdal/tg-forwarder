import { useEffect, useState } from 'react'
import RichTextEditor from './RichTextEditor'

// Красивая модалка для уведомлений и подтверждений
const Dialog = ({ isOpen, title, message, type, onConfirm, onCancel }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 sm:p-6">
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300" 
        onClick={onCancel}
      ></div>
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm flex flex-col overflow-hidden transform transition-all duration-300 scale-100 opacity-100">
        <div className="p-6 text-center">
          <div className={`mx-auto flex items-center justify-center h-16 w-16 rounded-full mb-4 ${type === 'error' ? 'bg-red-50' : type === 'confirm' ? 'bg-amber-50' : 'bg-blue-50'}`}>
            {type === 'error' && <span className="text-3xl">⚠️</span>}
            {type === 'confirm' && <span className="text-3xl">❓</span>}
            {type === 'info' && <span className="text-3xl">💬</span>}
            {type === 'success' && <span className="text-3xl">✅</span>}
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">{title || 'Уведомление'}</h3>
          <p className="text-gray-500 text-sm leading-relaxed whitespace-pre-wrap">{message}</p>
        </div>
        <div className="p-4 bg-gray-50 flex justify-center gap-3 border-t border-gray-100">
          {type === 'confirm' && (
            <button onClick={onCancel} className="px-4 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-xl font-bold hover:bg-gray-50 transition flex-1 shadow-sm">Отмена</button>
          )}
          <button onClick={onConfirm} className={`px-4 py-2.5 text-white rounded-xl font-bold transition shadow-md flex-1 ${type === 'error' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}>
            ОК
          </button>
        </div>
      </div>
    </div>
  );
};

// Красивая модалка для контента
const Modal = ({ isOpen, onClose, title, children, maxWidth = "max-w-2xl" }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300" 
        onClick={onClose}
      ></div>
      <div className={`relative bg-white rounded-2xl shadow-2xl w-full ${maxWidth} flex flex-col max-h-[90vh] overflow-hidden transform transition-all duration-300 scale-100 opacity-100`}>
        <div className="flex justify-between items-center p-4 sm:p-6 border-b border-gray-100 bg-gray-50/50">
          <h2 className="text-xl font-bold text-gray-800">{title}</h2>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition">&times;</button>
        </div>
        <div className="p-4 sm:p-6 overflow-y-auto flex-grow">
          {children}
        </div>
      </div>
    </div>
  );
};

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [password, setPassword] = useState("")
  
  const [activeTab, setActiveTab] = useState('posts')
  const [posts, setPosts] = useState([])
  const [trashPosts, setTrashPosts] = useState([])
  const [mediaLib, setMediaLib] = useState([])
  const [templates, setTemplates] = useState([])
  const [folders, setFolders] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [sources, setSources] = useState([])
  const [licenses, setLicenses] = useState([])
  const [loading, setLoading] = useState(true)
  
  const [status, setStatus] = useState({ bot_online: false, collector_online: false })
  const [license, setLicense] = useState(null)
  const [geminiKey, setGeminiKey] = useState("")
  const [geminiTesting, setGeminiTesting] = useState(false)
  const [geminiStatus, setGeminiStatus] = useState(null)
  
  const [queueSourceFilter, setQueueSourceFilter] = useState('all')

  const [editingPost, setEditingPost] = useState(null)
  const [editText, setEditText] = useState("")
  const [uploading, setUploading] = useState(false)
  const [attachMode, setAttachMode] = useState("append")
  const [selectedTemplate, setSelectedTemplate] = useState("")
  const [runningPipeline, setRunningPipeline] = useState(false)
  
  const [aiLoading, setAiLoading] = useState(false)
  const [linkClearing, setLinkClearing] = useState(false)
  const [aiPrompt, setAiPrompt] = useState("")
  const [aiGenerating, setAiGenerating] = useState(false)
  
  const [imagePrompt, setImagePrompt] = useState("")
  const [imageGenerating, setImageGenerating] = useState(false)
  const [imageWidth, setImageWidth] = useState(1080)
  const [imageHeight, setImageHeight] = useState(1080)
  const [imageModel, setImageModel] = useState("flux")
  const [imageSeed, setImageSeed] = useState("")
  const [imageModels, setImageModels] = useState(["flux", "turbo"])
  const [lastGeneratedMediaId, setLastGeneratedMediaId] = useState(null)
  const [libImageGenerating, setLibImageGenerating] = useState(false)
  const [libImagePrompt, setLibImagePrompt] = useState("")
  
  const [wordCount, setWordCount] = useState("")
  const [postButtons, setPostButtons] = useState([])
  
  const [showLibSelector, setShowLibSelector] = useState(false)
  const [libUploading, setLibUploading] = useState(false)
  const [refetching, setRefetching] = useState(false)
  const [cacheBuster, setCacheBuster] = useState(Date.now())
  const [clearing, setClearing] = useState(false)

  const [editingSource, setEditingSource] = useState(null)
  const [sourceTemplateId, setSourceTemplateId] = useState("")
  
  const [pipelineSource, setPipelineSource] = useState(null)
  const [pipelineSteps, setPipelineSteps] = useState([])
  const [savingPipeline, setSavingPipeline] = useState(false)

  const [newTemplate, setNewTemplate] = useState({ name: "", text: "", attach_mode: "append", folder_id: "", media_json: [], buttons_json: [] })
  const [editingTemplate, setEditingTemplate] = useState(null)
  const [editTemplateData, setEditTemplateData] = useState(null)
  const [newFolderName, setNewFolderName] = useState("")
  const [activeFolder, setActiveFolder] = useState(null)
  const [tplUploading, setTplUploading] = useState(false)
  const [editTplUploading, setEditTplUploading] = useState(false)

  const [newSourceInput, setNewSourceInput] = useState("")
  const [addingSource, setAddingSource] = useState(false)

  const [newLicClient, setNewLicClient] = useState("")
  const [newLicPlan, setNewLicPlan] = useState("pro")
  const [newLicDays, setNewLicDays] = useState(365)
  const [generatingLic, setGeneratingLic] = useState(false)
  const [generatedKey, setGeneratedKey] = useState("")
  const [coverLetter, setCoverLetter] = useState("")

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [viewAs, setViewAs] = useState(localStorage.getItem('viewAs') || 'owner')
  
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [upgradeFeature, setUpgradeFeature] = useState("")

  // Стейт для красивого Диалога
  const [dialog, setDialog] = useState({ isOpen: false, title: "", message: "", type: "info", onConfirm: null, onCancel: null });

  const showAlert = (message, title = "Уведомление", type = "info") => {
    setDialog({ isOpen: true, title, message, type, onConfirm: null, onCancel: () => setDialog(prev => ({ ...prev, isOpen: false })) });
  };

  const showConfirm = (message, onConfirm, title = "Подтверждение") => {
    setDialog({ 
      isOpen: true, 
      title, 
      message, 
      type: "confirm", 
      onConfirm: () => { onConfirm(); setDialog(prev => ({ ...prev, isOpen: false })); },
      onCancel: () => setDialog(prev => ({ ...prev, isOpen: false }))
    });
  };

  const fetchWithAuth = async (url, options = {}) => {
    const headers = { 
      ...options.headers, 
      'Authorization': `Bearer ${token}`,
      'X-View-As': viewAs
    }
    const res = await fetch(url, { ...options, headers })
    if (res.status === 401 || res.status === 403) {
      if (res.status === 401) { localStorage.removeItem('token'); setToken(null); }
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Forbidden");
    }
    return res
  }

  const fetchData = async () => {
    if (!token) return
    try {
      const [postsRes, trashRes, libRes, tplRes, foldRes, metRes, srcRes, licInfoRes, setRes] = await Promise.all([
        fetchWithAuth('/api/posts?trash=false'),
        fetchWithAuth('/api/posts?trash=true'),
        fetchWithAuth('/api/media-library'),
        fetchWithAuth('/api/templates'),
        fetchWithAuth('/api/template-folders'),
        fetchWithAuth('/api/metrics'),
        fetchWithAuth('/api/sources'),
        fetchWithAuth('/api/license/info'),
        fetchWithAuth('/api/settings')
      ])
      setPosts(await postsRes.json()); setTrashPosts(await trashRes.json());
      setMediaLib(await libRes.json()); setTemplates(await tplRes.json()); 
      setFolders(await foldRes.json()); setMetrics(await metRes.json()); setSources(await srcRes.json());
      
      const licData = await licInfoRes.json();
      setLicense(licData);

      const settingsData = await setRes.json();
      if (settingsData.gemini_api_key) setGeminiKey(settingsData.gemini_api_key);

      if (licData.plan === 'owner' && viewAs === 'owner') {
        const licListRes = await fetchWithAuth('/api/admin/licenses');
        setLicenses(await licListRes.json());
      }
    } catch (err) { console.error(err) } finally { setLoading(false) }
  }

  const fetchStatus = async () => {
    if (!token) return
    try {
      const res = await fetchWithAuth('/api/status')
      setStatus(await res.json())
    } catch (err) {}
  }

  useEffect(() => {
    localStorage.setItem('viewAs', viewAs);
    if (token) {
      setLoading(true);
      fetchData();
    }
  }, [viewAs, token]);

  useEffect(() => {
    if (activeTab === 'licenses' && viewAs !== 'owner') {
      setActiveTab('posts');
    }
  }, [viewAs, activeTab]);

  useEffect(() => { 
    if (token) {
      fetchData();
      fetchStatus();
      const interval = setInterval(() => {
        fetchData();
        fetchStatus();
      }, 10000);
      return () => clearInterval(interval);
    } 
  }, [token])

  useEffect(() => {
    if (token && license?.limits?.image_gen_enabled) {
      fetchWithAuth('/api/ai/image-models')
        .then(r => r.json())
        .then(d => { if (d.models?.length) setImageModels(d.models); })
        .catch(() => {});
    }
  }, [token, license]);

  useEffect(() => {
    window.onTelegramAuth = async (user) => {
      try {
        const res = await fetch('/api/auth/telegram', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(user) })
        if (res.ok) { const data = await res.json(); localStorage.setItem('token', data.token); setToken(data.token) }
      } catch (e) { showAlert("Ошибка сети", "Ошибка", "error") }
    }
    const container = document.getElementById('telegram-login-container')
    if (container && !token) {
      const script = document.createElement('script')
      script.src = "https://telegram.org/js/telegram-widget.js?22"
      script.setAttribute('data-telegram-login', 'tel_forw_bot')
      script.setAttribute('data-size', 'large'); script.setAttribute('data-onauth', 'onTelegramAuth(user)')
      script.async = true; container.appendChild(script)
    }
  }, [token])

  const handleDevLogin = async (e) => {
    e.preventDefault()
    try {
      const res = await fetch('/api/auth/dev', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) })
      if (res.ok) { const data = await res.json(); localStorage.setItem('token', data.token); setToken(data.token) }
      else showAlert("Неверный пароль", "Ошибка", "error")
    } catch (err) { showAlert("Ошибка сети", "Ошибка", "error") }
  }

  const handleSaveGemini = async () => {
    try {
      await fetchWithAuth('/api/settings/gemini', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: geminiKey })
      });
      showAlert("Ключ сохранен!", "Успех", "success");
    } catch (err) { showAlert("Ошибка сохранения", "Ошибка", "error"); }
  }

  const handleTestGemini = async () => {
    setGeminiTesting(true); setGeminiStatus(null);
    try {
      const res = await fetchWithAuth('/api/settings/gemini/test', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: geminiKey })
      });
      const data = await res.json();
      if (res.ok) setGeminiStatus({ type: 'success', msg: data.message });
      else setGeminiStatus({ type: 'error', msg: data.detail });
    } catch (err) { setGeminiStatus({ type: 'error', msg: "Ошибка сети" }); }
    finally { setGeminiTesting(false); }
  }

  const openPipeline = (source) => {
    setPipelineSource(source);
    try { setPipelineSteps(JSON.parse(source.pipeline_json || '[]')); } catch { setPipelineSteps([]); }
  }

  const addPipelineStep = (type) => {
    const newStep = { type, params: {} };
    if (type === 'rewrite') newStep.params.words = 30;
    if (type === 'generate_text') newStep.params.prompt = "";
    if (type === 'generate_image') { newStep.params.prompt = ""; newStep.params.width = 1080; newStep.params.height = 1080; }
    setPipelineSteps([...pipelineSteps, newStep]);
  }

  const updatePipelineStep = (index, field, value) => {
    const newSteps = [...pipelineSteps];
    if (field === 'type') {
      newSteps[index] = { type: value, params: {} };
      if (value === 'rewrite') newSteps[index].params.words = 30;
      if (value === 'generate_text') newSteps[index].params.prompt = "";
      if (value === 'generate_image') { newSteps[index].params.prompt = ""; newSteps[index].params.width = 1080; newSteps[index].params.height = 1080; }
    } else {
      newSteps[index].params[field] = value;
    }
    setPipelineSteps(newSteps);
  }

  const movePipelineStep = (index, direction) => {
    const newSteps = [...pipelineSteps];
    if (direction === 'up' && index > 0) [newSteps[index - 1], newSteps[index]] = [newSteps[index], newSteps[index - 1]];
    else if (direction === 'down' && index < newSteps.length - 1) [newSteps[index + 1], newSteps[index]] = [newSteps[index], newSteps[index + 1]];
    setPipelineSteps(newSteps);
  }

  const savePipeline = async () => {
    setSavingPipeline(true);
    try {
      await fetchWithAuth(`/api/sources/${pipelineSource.id}/pipeline`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps: pipelineSteps })
      });
      setPipelineSource(null); fetchData();
    } catch (err) { showAlert("Ошибка сохранения", "Ошибка", "error"); } finally { setSavingPipeline(false); }
  }

  const handleRunPipeline = async () => {
    if (!aiEnabled) { setUpgradeFeature("Прогон цепочки"); setShowUpgradeModal(true); return; }
    showConfirm("Прогнать цепочку? Текущий текст будет перезаписан.", async () => {
      setRunningPipeline(true);
      try {
        const res = await fetchWithAuth(`/api/posts/${editingPost.id}/run-pipeline`, { method: 'POST' });
        if (res.ok) {
          setCacheBuster(Date.now());
          const updated = await fetchWithAuth(`/api/posts/${editingPost.id}`).then(r => r.json());
          setEditingPost(updated); setEditText(updated.text || ""); fetchData();
        } else showAlert((await res.json()).detail, "Ошибка", "error");
      } catch (err) { showAlert(err.message, "Ошибка", "error"); } finally { setRunningPipeline(false); }
    });
  }

  const handleCreateLicense = async (e) => {
    e.preventDefault(); if (!newLicClient.trim()) return showAlert("Введите имя клиента", "Внимание", "error");
    setGeneratingLic(true);
    try {
      const res = await fetchWithAuth('/api/admin/licenses', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: newLicClient, plan: newLicPlan, days: parseInt(newLicDays) })
      });
      if (res.ok) {
        const data = await res.json();
        setGeneratedKey(data.license_key);
        setCoverLetter(`Спасибо за покупку TG Forwarder! 🚀\n\n1. Скачайте архив...\n2. Запустите install...\n3. Введите ключ:\n${data.license_key}`);
        setNewLicClient(""); fetchData();
      } else showAlert(`Ошибка: ${(await res.json()).detail}`, "Ошибка", "error");
    } finally { setGeneratingLic(false); }
  }

  const handleToggleLicense = async (id) => { await fetchWithAuth(`/api/admin/licenses/${id}/toggle`, { method: 'PATCH' }); fetchData(); }
  const handleDeleteLicense = async (id) => { 
    showConfirm("Удалить запись о лицензии?", async () => {
      await fetchWithAuth(`/api/admin/licenses/${id}`, { method: 'DELETE' }); fetchData(); 
    });
  }
  const copyToClipboard = (text) => { navigator.clipboard.writeText(text); showAlert("Скопировано!", "Успех", "success"); }
  const downloadZip = async () => {
    try {
      const res = await fetchWithAuth('/api/admin/download-latest')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = 'tg-forwarder.zip'
      document.body.appendChild(a); a.click(); a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) { showAlert(err.message, "Ошибка", "error") }
  }

  const handleClearChannel = async () => { 
    showConfirm("Удалить все сообщения из канала?", async () => {
      setClearing(true); 
      try { const res = await fetchWithAuth('/api/target-channel/clear', { method: 'POST' }); if (res.ok) showAlert((await res.json()).message, "Успех", "success"); else showAlert((await res.json()).detail, "Ошибка", "error"); } finally { setClearing(false); } 
    });
  }
  
  const handleAction = async (postId, action) => { try { const method = action === 'purge' ? 'DELETE' : 'POST'; if ((await fetchWithAuth(`/api/posts/${postId}/${action}`, { method })).ok) fetchData() } catch (err) { showAlert("Ошибка", "Ошибка", "error") } }
  
  const handleEmptyTrash = async () => { 
    showConfirm("Удалить ВСЕ посты из корзины?", async () => {
      if ((await fetchWithAuth(`/api/posts/trash/empty`, { method: 'DELETE' })).ok) fetchData(); 
    });
  }
  
  const handleRefetch = async (postId) => { 
    setRefetching(true); 
    try { const res = await fetchWithAuth(`/api/posts/${postId}/refetch`, { method: 'POST' }); if (res.ok) { showAlert((await res.json()).message, "Успех", "success"); setCacheBuster(Date.now()); const single = await fetchWithAuth(`/api/posts/${postId}`).then(r => r.json()); setEditingPost(single); fetchData(); } else showAlert((await res.json()).detail, "Ошибка", "error"); } finally { setRefetching(false); } 
  }
  
  const handleCreateManualPost = async () => { try { const res = await fetchWithAuth('/api/manual-post', { method: 'POST' }); if (res.ok) { const data = await res.json(); const newPost = await fetchWithAuth(`/api/posts/${data.id}`).then(r => r.json()); setEditingPost(newPost); setEditText(""); setPostButtons([]); setAiPrompt(""); setImagePrompt(""); setLastGeneratedMediaId(null); fetchData(); } else showAlert(`Ошибка: ${(await res.json()).detail}`, "Ошибка", "error"); } catch (err) { showAlert("Ошибка сети", "Ошибка", "error"); } }
  
  const saveEdit = async () => { try { await fetchWithAuth(`/api/posts/${editingPost.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: editText, buttons_json: postButtons.filter(b => b.text && b.url) }) }); closeEditor(); fetchData(); } catch (err) { showAlert("Ошибка", "Ошибка", "error"); } }
  
  const handleTranslate = async () => { 
    if (!aiEnabled) { setUpgradeFeature("Перевод текста"); setShowUpgradeModal(true); return; }
    if (!editText) return; setAiLoading(true); 
    try { const res = await fetchWithAuth('/api/ai/translate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: editText }) }); if (res.ok) setEditText((await res.json()).result); else showAlert((await res.json()).detail, "Ошибка", "error"); } catch (err) { showAlert(err.message, "Ошибка", "error"); } finally { setAiLoading(false); } 
  }
  
  const handleRewrite = async () => { 
    if (!aiEnabled) { setUpgradeFeature("Рерайт текста"); setShowUpgradeModal(true); return; }
    if (!editText) return; setAiLoading(true); 
    try { const res = await fetchWithAuth('/api/ai/rewrite', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: editText, word_count: wordCount ? parseInt(wordCount) : null }) }); if (res.ok) setEditText((await res.json()).result); else showAlert((await res.json()).detail, "Ошибка", "error"); } catch (err) { showAlert(err.message, "Ошибка", "error"); } finally { setAiLoading(false); } 
  }
  
  const handleClearLinks = async () => { 
    if (!editText) return; setLinkClearing(true); 
    try { const res = await fetchWithAuth('/api/ai/remove-links', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: editText }) }); if (res.ok) setEditText((await res.json()).result); } finally { setLinkClearing(false); } 
  }
  
  const handleGenerateText = async () => { 
    if (!aiEnabled) { setUpgradeFeature("Написание текста через ИИ"); setShowUpgradeModal(true); return; }
    if (!aiPrompt.trim()) return showAlert("Напиши задание", "Внимание", "error"); 
    setAiGenerating(true); 
    try { const res = await fetchWithAuth('/api/ai/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: aiPrompt, base_text: editText }) }); if (res.ok) setEditText((await res.json()).result); else showAlert(`Ошибка: ${(await res.json()).detail}`, "Ошибка", "error"); } catch (err) { showAlert(err.message, "Ошибка", "error"); } finally { setAiGenerating(false); } 
  }
  
  const handleGenerateImage = async (overridePrompt = null, replaceMediaId = null) => { 
    if (!imgEnabled) { setUpgradeFeature("Генерация картинок"); setShowUpgradeModal(true); return; }
    const p = overridePrompt ?? imagePrompt; if (!p.trim()) return showAlert("Введи промпт", "Внимание", "error"); 
    setImageGenerating(true); 
    try { if (replaceMediaId) { await fetchWithAuth(`/api/media/${replaceMediaId}`, { method: 'DELETE' }).catch(()=>{}); } const res = await fetchWithAuth('/api/ai/generate-image', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: p, post_id: editingPost.id, width: parseInt(imageWidth), height: parseInt(imageHeight), model: imageModel, seed: imageSeed ? parseInt(imageSeed) : null }) }); if (res.ok) { const data = await res.json(); setCacheBuster(Date.now()); setLastGeneratedMediaId(data.media_id || null); const updated = await fetchWithAuth(`/api/posts/${editingPost.id}`).then(r => r.json()); setEditingPost(updated); if (!overridePrompt) setImagePrompt(""); fetchData(); } else showAlert(`Ошибка: ${(await res.json()).detail}`, "Ошибка", "error"); } catch (err) { showAlert(err.message, "Ошибка", "error"); } finally { setImageGenerating(false); } 
  }
  
  const handleGenerateLibraryImage = async () => { 
    if (!imgEnabled) { setUpgradeFeature("Генерация картинок"); setShowUpgradeModal(true); return; }
    if (!libImagePrompt.trim()) return showAlert("Введи промпт", "Внимание", "error"); 
    setLibImageGenerating(true); 
    try { const res = await fetchWithAuth('/api/ai/generate-image', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: libImagePrompt, width: parseInt(imageWidth), height: parseInt(imageHeight), model: imageModel, seed: imageSeed ? parseInt(imageSeed) : null }) }); if (res.ok) { setCacheBuster(Date.now()); setLibImagePrompt(""); showAlert("Сохранено!", "Успех", "success"); fetchData(); } else showAlert(`Ошибка: ${(await res.json()).detail}`, "Ошибка", "error"); } catch (err) { showAlert(err.message, "Ошибка", "error"); } finally { setLibImageGenerating(false); } 
  }
  
  const handleUploadMedia = async (e) => { const file = e.target.files[0]; if (!file) return; setUploading(true); const formData = new FormData(); formData.append('file', file); try { await fetchWithAuth(`/api/posts/${editingPost.id}/media`, { method: 'POST', body: formData }); setCacheBuster(Date.now()); const updated = await fetchWithAuth(`/api/posts/${editingPost.id}`).then(r => r.json()); setEditingPost(updated); fetchData(); } finally { setUploading(false); e.target.value = null; } }
  
  const handleDeleteMedia = async (mediaId) => { 
    showConfirm("Удалить медиа?", async () => {
      const res = await fetchWithAuth(`/api/media/${mediaId}`, { method: 'DELETE' }); if (!res.ok) return showAlert("Ошибка удаления", "Ошибка", "error"); const updated = await fetchWithAuth(`/api/posts/${editingPost.id}`).then(r => r.json()); setEditingPost(updated); fetchData();
    });
  }
  
  const handleSaveToLib = async (mediaId) => { try { const res = await fetchWithAuth(`/api/posts/${editingPost.id}/media/save-to-library/${mediaId}`, { method: 'POST' }); if (res.ok) { fetchData(); showAlert("Медиа сохранено в библиотеку!", "Успех", "success"); } else showAlert(`${(await res.json()).detail}`, "Ошибка", "error"); } catch (err) { showAlert("Ошибка сети", "Ошибка", "error"); } }
  
  const handleAttachFromLib = async (libId) => { const res = await fetchWithAuth(`/api/posts/${editingPost.id}/media/from-library/${libId}`, { method: 'POST' }); if (!res.ok) return showAlert("Ошибка прикрепления", "Ошибка", "error"); setCacheBuster(Date.now()); const updated = await fetchWithAuth(`/api/posts/${editingPost.id}`).then(r => r.json()); setEditingPost(updated); setShowLibSelector(false); fetchData(); }
  
  const handleUploadToLib = async (e) => { const file = e.target.files[0]; if (!file) return; setLibUploading(true); const formData = new FormData(); formData.append('file', file); try { await fetchWithAuth('/api/media-library/upload', { method: 'POST', body: formData }); setCacheBuster(Date.now()); fetchData(); } finally { setLibUploading(false); e.target.value = null; } }
  
  const handleDeleteFromLib = async (libId) => { 
    showConfirm("Удалить файл из библиотеки?", async () => {
      await fetchWithAuth(`/api/media-library/${libId}`, { method: 'DELETE' }); fetchData(); 
    });
  }
  
  const handleDownload = async (key, type) => { try { const response = await fetch(`/media/${key}`); if (!response.ok) throw new Error("Ошибка"); const blob = await response.blob(); const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `media_${Date.now()}.${key.split('.').pop() || 'jpg'}`; document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(url); } catch (err) { showAlert("Ошибка скачивания", "Ошибка", "error"); } }
  
  const handleAttachTemplate = async () => { if (!selectedTemplate) return; const res = await fetchWithAuth(`/api/posts/${editingPost.id}/templates`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ template_id: parseInt(selectedTemplate), mode: attachMode }) }); if (!res.ok) return showAlert(`Ошибка: ${(await res.json()).detail}`, "Ошибка", "error"); const updated = await fetchWithAuth(`/api/posts/${editingPost.id}`).then(r => r.json()); setEditingPost(updated); fetchData(); setSelectedTemplate(""); }
  
  const handleDetachTemplate = async (tplId) => { const res = await fetchWithAuth(`/api/posts/${editingPost.id}/templates/${tplId}`, { method: 'DELETE' }); if (!res.ok) return showAlert("Ошибка", "Ошибка", "error"); const updated = await fetchWithAuth(`/api/posts/${editingPost.id}`).then(r => r.json()); setEditingPost(updated); fetchData(); }
  
  const handleAttachSourceTemplate = async () => { if (!sourceTemplateId) return; await fetchWithAuth(`/api/sources/${editingSource.id}/templates`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ template_id: parseInt(sourceTemplateId) }) }); const updatedSources = await fetchWithAuth('/api/sources').then(r => r.json()); setEditingSource(updatedSources.find(s => s.id === editingSource.id)); setSourceTemplateId(""); fetchData(); }
  
  const handleDetachSourceTemplate = async (tplId) => { await fetchWithAuth(`/api/sources/${editingSource.id}/templates/${tplId}`, { method: 'DELETE' }); const updatedSources = await fetchWithAuth('/api/sources').then(r => r.json()); setEditingSource(updatedSources.find(s => s.id === editingSource.id)); fetchData(); }
  
  const handleToggleAutoPublish = async (source, checked) => { await fetchWithAuth(`/api/sources/${source.id}/auto-publish`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ auto_publish: checked, auto_template_id: checked ? source.auto_template_id : null }) }); fetchData(); }
  
  const handleSetAutoTemplate = async (source, templateId) => { await fetchWithAuth(`/api/sources/${source.id}/auto-publish`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ auto_publish: source.auto_publish, auto_template_id: templateId ? parseInt(templateId) : null }) }); fetchData(); }
  
  const openEditTemplate = (tpl) => { setEditingTemplate(tpl); setEditTemplateData({ name: tpl.name, text: tpl.text || "", attach_mode: tpl.mode, folder_id: tpl.folder_id || "", media_json: JSON.parse(JSON.stringify(tpl.media_json || [])), buttons_json: JSON.parse(JSON.stringify(tpl.buttons_json || [])) }); }
  
  const closeEditTemplate = () => { setEditingTemplate(null); setEditTemplateData(null); }
  
  const handleUpdateTemplate = async (e) => { e.preventDefault(); const cleanButtons = editTemplateData.buttons_json.filter(b => b.text && b.url); const res = await fetchWithAuth(`/api/templates/${editingTemplate.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...editTemplateData, buttons_json: cleanButtons, folder_id: editTemplateData.folder_id ? parseInt(editTemplateData.folder_id) : null }) }); if (!res.ok) return showAlert("Ошибка обновления шаблона", "Ошибка", "error"); closeEditTemplate(); fetchData(); }
  
  const handleUploadEditTemplateMedia = async (e) => { const file = e.target.files[0]; if (!file) return; setEditTplUploading(true); const formData = new FormData(); formData.append('file', file); try { const res = await fetchWithAuth('/api/upload', { method: 'POST', body: formData }); if (res.ok) { const data = await res.json(); setEditTemplateData(prev => ({ ...prev, media_json: [...(prev.media_json || []), data] })); } } finally { setEditTplUploading(false); e.target.value = null; } }
  
  const removeEditTemplateMedia = (index) => { setEditTemplateData(prev => ({ ...prev, media_json: prev.media_json.filter((_, i) => i !== index) })); }
  const addEditTemplateButton = () => { setEditTemplateData(prev => ({ ...prev, buttons_json: [...(prev.buttons_json || []), { text: "", url: "" }] })); }
  const updateEditTemplateButton = (idx, field, value) => { const nb = [...editTemplateData.buttons_json]; nb[idx][field] = value; setEditTemplateData({ ...editTemplateData, buttons_json: nb }); }
  const removeEditTemplateButton = (idx) => { setEditTemplateData(prev => ({ ...prev, buttons_json: prev.buttons_json.filter((_, i) => i !== idx) })); }
  
  const handleUploadTemplateMedia = async (e) => { const file = e.target.files[0]; if (!file) return; setTplUploading(true); const formData = new FormData(); formData.append('file', file); try { const res = await fetchWithAuth('/api/upload', { method: 'POST', body: formData }); if (res.ok) { const data = await res.json(); setNewTemplate(prev => ({ ...prev, media_json: [...(prev.media_json || []), data] })); } } finally { setTplUploading(false); e.target.value = null; } }
  
  const removeTemplateMedia = (index) => setNewTemplate(prev => ({ ...prev, media_json: prev.media_json.filter((_, i) => i !== index) }));
  const addTemplateButton = () => setNewTemplate(prev => ({ ...prev, buttons_json: [...(prev.buttons_json || []), { text: "", url: "" }] }));
  const updateTemplateButton = (idx, field, value) => { const nb = [...newTemplate.buttons_json]; nb[idx][field] = value; setNewTemplate({ ...newTemplate, buttons_json: nb }); };
  const removeTemplateButton = (idx) => setNewTemplate(prev => ({ ...prev, buttons_json: prev.buttons_json.filter((_, i) => i !== idx) }));
  
  const handleCreateTemplate = async (e) => { e.preventDefault(); const cleanButtons = newTemplate.buttons_json.filter(b => b.text && b.url); await fetchWithAuth('/api/templates', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...newTemplate, buttons_json: cleanButtons, folder_id: newTemplate.folder_id ? parseInt(newTemplate.folder_id) : null }) }); setNewTemplate({ name: "", text: "", attach_mode: "append", folder_id: activeFolder || "", media_json: [], buttons_json: [] }); fetchData(); }
  
  const handleDeleteTemplate = async (id) => { 
    showConfirm("Удалить шаблон?", async () => {
      await fetchWithAuth(`/api/templates/${id}`, { method: 'DELETE' }); fetchData(); 
    });
  }
  
  const handleCreateFolder = async (e) => { e.preventDefault(); if (!newFolderName) return; await fetchWithAuth('/api/template-folders', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newFolderName }) }); setNewFolderName(""); fetchData(); }
  
  const handleDeleteFolder = async (id) => { 
    showConfirm("Удалить папку?", async () => {
      await fetchWithAuth(`/api/template-folders/${id}`, { method: 'DELETE' }); if (activeFolder === id) setActiveFolder(null); fetchData(); 
    });
  }
  
  const handleAddSource = async (e) => { 
    e.preventDefault(); if (!newSourceInput) return; setAddingSource(true); 
    try { 
      const res = await fetchWithAuth('/api/sources', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ channel_input: newSourceInput }) }); 
      if (res.ok) { setNewSourceInput(""); fetchData(); } else showAlert(`Ошибка: ${(await res.json()).detail}`, "Ошибка", "error"); 
    } catch (err) { showAlert(err.message, "Ошибка", "error"); } finally { setAddingSource(false); } 
  }
  
  const handleToggleSource = async (id) => { await fetchWithAuth(`/api/sources/${id}/toggle`, { method: 'PATCH' }); fetchData(); }
  
  const handleDeleteSource = async (id) => { 
    showConfirm("Удалить источник?", async () => {
      await fetchWithAuth(`/api/sources/${id}`, { method: 'DELETE' }); fetchData(); 
    });
  }
  
  const openEditor = (post) => { setEditingPost(post); setEditText(post.text || ""); setWordCount(""); setPostButtons(post.buttons_json || []); setAiPrompt(""); setImagePrompt(""); setLastGeneratedMediaId(null); }
  const closeEditor = () => { setEditingPost(null); setEditText(""); setPostButtons([]); setShowLibSelector(false); setAiPrompt(""); setImagePrompt(""); setLastGeneratedMediaId(null); }
  
  const getMediaUrl = (key) => `/media/${key}?v=${cacheBuster}`
  const getStatusColor = (status) => ({ new: 'bg-blue-100 text-blue-800', published: 'bg-green-100 text-green-800', scheduled: 'bg-yellow-100 text-yellow-800', deleted: 'bg-red-100 text-red-800' }[status] || 'bg-gray-100')

  const isOwner = license?.plan === 'owner'
  const aiEnabled = license?.limits?.ai_enabled ?? true
  const imgEnabled = license?.limits?.image_gen_enabled ?? true
  const maxSources = license?.limits?.max_sources ?? 5
  const sourcesLimitReached = maxSources !== -1 && sources.length >= maxSources

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
          <h1 className="text-2xl font-bold text-center mb-6">Вход в TG Forwarder</h1>
          <div className="mb-6"><div id="telegram-login-container" className="flex justify-center"></div></div>
          <form onSubmit={handleDevLogin}>
            <input type="password" placeholder="JWT_SECRET из .env" className="w-full p-3 border rounded mb-4" value={password} onChange={e => setPassword(e.target.value)} />
            <button type="submit" className="w-full bg-blue-600 text-white py-3 rounded font-bold hover:bg-blue-700">Войти</button>
          </form>
        </div>
        <Dialog {...dialog} />
      </div>
    )
  }

  if (loading) return <div className="text-center mt-20 text-xl">Загрузка...</div>
  
  const filteredTemplates = activeFolder ? templates.filter(t => t.folder_id === activeFolder) : templates
  const filteredQueuePosts = queueSourceFilter === 'all' ? posts : posts.filter(p => p.source === queueSourceFilter)

  const MobileSidebar = () => (
    <div className={`fixed inset-0 z-[100] md:hidden transition-opacity duration-300 ${isMobileMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}>
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setIsMobileMenuOpen(false)}></div>
      <div className={`absolute top-0 left-0 h-full w-64 bg-white shadow-2xl transform transition-transform duration-300 ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} flex flex-col`}>
        <div className="p-4 border-b flex justify-between items-center bg-gray-50">
          <span className="font-bold text-lg text-gray-800">📨 Меню</span>
          <button onClick={() => setIsMobileMenuOpen(false)} className="text-3xl leading-none text-gray-500 hover:text-black">&times;</button>
        </div>
        <div className="flex-grow overflow-y-auto p-4 flex flex-col gap-1">
          <button onClick={() => { setActiveTab('posts'); setIsMobileMenuOpen(false); }} className={`w-full text-left px-4 py-3 rounded-lg font-bold text-lg ${activeTab === 'posts' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}`}>Очередь</button>
          <button onClick={() => { setActiveTab('trash'); setIsMobileMenuOpen(false); }} className={`w-full text-left px-4 py-3 rounded-lg font-bold text-lg ${activeTab === 'trash' ? 'bg-red-50 text-red-700' : 'text-gray-700 hover:bg-gray-100'}`}>Корзина</button>
          <button onClick={() => { setActiveTab('media'); setIsMobileMenuOpen(false); }} className={`w-full text-left px-4 py-3 rounded-lg font-bold text-lg ${activeTab === 'media' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}`}>Медиа</button>
          <button onClick={() => { setActiveTab('sources'); setIsMobileMenuOpen(false); }} className={`w-full text-left px-4 py-3 rounded-lg font-bold text-lg ${activeTab === 'sources' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}`}>Источники</button>
          <button onClick={() => { setActiveTab('templates'); setIsMobileMenuOpen(false); }} className={`w-full text-left px-4 py-3 rounded-lg font-bold text-lg ${activeTab === 'templates' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}`}>Шаблоны</button>
          <button onClick={() => { setActiveTab('metrics'); setIsMobileMenuOpen(false); }} className={`w-full text-left px-4 py-3 rounded-lg font-bold text-lg ${activeTab === 'metrics' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}`}>Метрики</button>
          <button onClick={() => { setActiveTab('settings'); setIsMobileMenuOpen(false); }} className={`w-full text-left px-4 py-3 rounded-lg font-bold text-lg ${activeTab === 'settings' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}`}>Настройки</button>
          {isOwner && viewAs === 'owner' && <button onClick={() => { setActiveTab('licenses'); setIsMobileMenuOpen(false); }} className={`w-full text-left px-4 py-3 rounded-lg font-bold text-lg ${activeTab === 'licenses' ? 'bg-purple-50 text-purple-700' : 'text-gray-700 hover:bg-gray-100'}`}>Лицензии</button>}
        </div>
        <div className="p-4 border-t bg-gray-50">
          <button onClick={() => { localStorage.removeItem('token'); setToken(null); }} className="w-full bg-red-100 text-red-700 font-bold py-2 rounded-lg">Выйти</button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto p-4">
      <MobileSidebar />
      <Dialog {...dialog} />

      {viewAs !== 'owner' && (
        <div className="bg-red-500 text-white text-center py-2 px-4 text-sm font-bold sticky top-0 z-[90] shadow-lg mb-4 rounded-lg flex flex-col sm:flex-row justify-center items-center gap-2 sm:gap-4">
          <span>⚠️ РЕЖИМ ПРОСМОТРА: {viewAs.toUpperCase()}</span>
          <button onClick={() => setViewAs('owner')} className="bg-white text-red-500 px-3 py-1 rounded text-xs hover:bg-red-50 transition">Выйти из режима</button>
        </div>
      )}

      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-6 border-b pb-4 gap-4">
        <div className="flex items-center gap-4 w-full xl:w-auto">
          <button onClick={() => setIsMobileMenuOpen(true)} className="md:hidden p-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
          </button>
          <div className="hidden md:block w-full md:w-auto overflow-x-auto whitespace-nowrap pb-2 md:pb-0">
            <div className="flex gap-4 items-center">
              <button onClick={() => setActiveTab('posts')} className={`text-lg xl:text-xl font-bold ${activeTab === 'posts' ? 'text-blue-600' : 'text-gray-400'}`}>Очередь</button>
              <button onClick={() => setActiveTab('trash')} className={`text-lg xl:text-xl font-bold ${activeTab === 'trash' ? 'text-red-600' : 'text-gray-400'}`}>Корзина</button>
              <button onClick={() => setActiveTab('media')} className={`text-lg xl:text-xl font-bold ${activeTab === 'media' ? 'text-blue-600' : 'text-gray-400'}`}>Медиа</button>
              <button onClick={() => setActiveTab('sources')} className={`text-lg xl:text-xl font-bold ${activeTab === 'sources' ? 'text-blue-600' : 'text-gray-400'}`}>Источники</button>
              <button onClick={() => setActiveTab('templates')} className={`text-lg xl:text-xl font-bold ${activeTab === 'templates' ? 'text-blue-600' : 'text-gray-400'}`}>Шаблоны</button>
              <button onClick={() => setActiveTab('metrics')} className={`text-lg xl:text-xl font-bold ${activeTab === 'metrics' ? 'text-blue-600' : 'text-gray-400'}`}>Метрики</button>
              <button onClick={() => setActiveTab('settings')} className={`text-lg xl:text-xl font-bold ${activeTab === 'settings' ? 'text-blue-600' : 'text-gray-400'}`}>Настройки</button>
              {isOwner && viewAs === 'owner' && <button onClick={() => setActiveTab('licenses')} className={`text-lg xl:text-xl font-bold ${activeTab === 'licenses' ? 'text-purple-600' : 'text-gray-400'}`}>Лицензии</button>}
            </div>
          </div>
        </div>
        
        <div className="flex flex-wrap gap-4 items-center justify-between w-full xl:w-auto">
          <div className="flex gap-2 sm:gap-4 text-sm font-medium items-center flex-wrap">
            {license?.plan === 'owner' && (
              <select 
                value={viewAs} 
                onChange={(e) => setViewAs(e.target.value)}
                className="border rounded p-1 text-sm bg-purple-50 text-purple-700 font-bold outline-none cursor-pointer"
              >
                <option value="owner">👑 Owner</option>
                <option value="business">Business</option>
                <option value="pro">Pro</option>
                <option value="free">Free</option>
              </select>
            )}
            
            {license && viewAs === 'owner' && (
              <div className="flex items-center gap-2 bg-indigo-50 px-2 py-1 rounded border border-indigo-200">
                <span className="text-xs font-bold text-indigo-700 uppercase">{license.plan}</span>
                <span className="text-xs text-indigo-500">({maxSources === -1 ? '∞' : maxSources} ист.)</span>
              </div>
            )}
            
            <div className="flex items-center gap-2 bg-gray-50 px-2 py-1 rounded border">
              <span className={`w-2.5 h-2.5 rounded-full ${status.bot_online ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              <span className={status.bot_online ? 'text-green-700' : 'text-red-700'}>Бот</span>
            </div>
            <div className="flex items-center gap-2 bg-gray-50 px-2 py-1 rounded border">
              <span className={`w-2.5 h-2.5 rounded-full ${status.collector_online ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              <span className={status.collector_online ? 'text-green-700' : 'text-red-700'}>Сборщик</span>
            </div>
          </div>
          <button onClick={() => { localStorage.removeItem('token'); setToken(null); }} className="hidden md:block text-sm text-red-500 hover:underline ml-auto xl:ml-0">Выйти</button>
        </div>
      </div>
      
      {activeTab === 'posts' && (
        <div className="flex flex-col lg:flex-row gap-6">
          <div className="w-full lg:w-1/4 bg-white p-4 rounded shadow h-fit flex flex-col gap-4">
            <button onClick={handleCreateManualPost} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded font-bold shadow transition">➕ Создать пост</button>
            <div>
              <h2 className="text-lg font-bold mb-4">Папки</h2>
              <ul className="space-y-1">
                <li><button onClick={() => setQueueSourceFilter('all')} className={`w-full flex justify-between items-center text-left px-3 py-2 rounded ${queueSourceFilter === 'all' ? 'bg-blue-100 font-bold text-blue-800' : 'hover:bg-gray-100'}`}><span>📁 Все посты</span><span className="text-xs bg-gray-200 px-2 py-0.5 rounded-full text-gray-600">{posts.length}</span></button></li>
                {sources.map(s => {
                  const count = posts.filter(p => p.source === s.username).length;
                  return (
                    <li key={s.id}><button onClick={() => setQueueSourceFilter(s.username)} className={`w-full flex justify-between items-center text-left px-3 py-2 rounded ${queueSourceFilter === s.username ? 'bg-blue-100 font-bold text-blue-800' : 'hover:bg-gray-100'}`}><span className="truncate pr-2">{s.username === 'manual' ? '✍️ Ручные' : `@${s.username}`}</span><span className="text-xs bg-gray-200 px-2 py-0.5 rounded-full text-gray-600">{count}</span></button></li>
                  )
                })}
              </ul>
            </div>
          </div>
          <div className="w-full lg:w-3/4">
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {filteredQueuePosts.map(post => (
                <div key={post.id} className="bg-white rounded-lg shadow-md overflow-hidden flex flex-col">
                  {post.media_count > 0 ? (
                    <div className="h-48 bg-gray-200 relative">
                      {post.media[0].type === 'video' ? <video src={getMediaUrl(post.media[0].key)} className="w-full h-full object-cover" controls /> : <img src={getMediaUrl(post.media[0].key)} className="w-full h-full object-cover" />}
                      {post.media_count > 1 && <span className="absolute top-2 right-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-sm z-10">+{post.media_count - 1} фото</span>}
                    </div>
                  ) : <div className="h-24 bg-gray-100 flex items-center justify-center text-gray-400">Без медиа</div>}
                  <div className="p-4 flex-grow flex flex-col">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-500">{post.source === 'manual' ? '✍️ Ручной' : `@${post.source}`}</span>
                      <span className={`text-xs px-2 py-1 rounded-full font-bold uppercase ${getStatusColor(post.status)}`}>{post.status}</span>
                    </div>
                    <p className="text-gray-700 text-sm flex-grow line-clamp-4 whitespace-pre-wrap">{post.text || 'Без текста'}</p>
                    <div className="mt-4 flex flex-col gap-2">
                      <button onClick={() => openEditor(post)} className="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 rounded text-sm font-medium">✏️ Редактировать</button>
                      {(post.status === 'new' || post.status === 'scheduled') && (
                        <div className="flex gap-2">
                          <button onClick={() => handleAction(post.id, 'approve')} className="flex-1 bg-green-500 text-white py-2 rounded text-sm">✅ Опубликовать</button>
                          <button onClick={() => handleAction(post.id, 'delete')} className="flex-1 bg-red-500 text-white py-2 rounded text-sm">🗑 В корзину</button>
                        </div>
                      )}
                      {post.status === 'published' && <button onClick={() => handleAction(post.id, 'unpublish')} className="w-full bg-orange-500 hover:bg-orange-600 text-white py-2 rounded text-sm font-medium">↩️ Отменить публикацию</button>}
                    </div>
                  </div>
                </div>
              ))}
              {filteredQueuePosts.length === 0 && <div className="col-span-full text-center py-10 text-gray-500">В этой папке нет постов</div>}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'media' && (
        <div>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
            <h2 className="text-2xl font-bold">Медиа-библиотека</h2>
            <div className="relative w-full sm:w-auto">
              <input type="file" onChange={handleUploadToLib} disabled={libUploading} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
              <button className="w-full sm:w-auto bg-blue-600 text-white px-4 py-2 rounded shadow text-sm font-bold">{libUploading ? 'Загрузка...' : '+ Загрузить файл'}</button>
            </div>
          </div>
          
          <div className="mb-6 bg-emerald-50 p-4 rounded-lg border border-emerald-200">
            <h3 className="text-sm font-bold text-emerald-800 mb-2">🎨 Сгенерировать картинку в библиотеку</h3>
            <div className="flex flex-wrap gap-2 mb-2">
              <select value={imageModel} onChange={e => setImageModel(e.target.value)} className="border rounded p-1 text-sm">{imageModels.map(m => <option key={m} value={m}>{m}</option>)}</select>
              <select value={`${imageWidth}x${imageHeight}`} onChange={e => { const [w, h] = e.target.value.split('x').map(Number); setImageWidth(w); setImageHeight(h); }} className="border rounded p-1 text-sm">
                <option value="1080x1080">Квадрат 1080×1080</option><option value="1080x1350">Портрет 1080×1350</option><option value="1920x1080">Альбом 1920×1080</option>
              </select>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <input placeholder="Промпт..." className="flex-grow p-2 border rounded text-sm" value={libImagePrompt} onChange={e => setLibImagePrompt(e.target.value)} disabled={libImageGenerating} />
              <button onClick={handleGenerateLibraryImage} disabled={libImageGenerating} className="w-full sm:w-auto bg-emerald-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50 whitespace-nowrap">{libImageGenerating ? 'Генерация...' : '🎨 Сгенерировать'}</button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {mediaLib.map(m => (
              <div key={m.id} className="bg-white rounded shadow overflow-hidden group relative h-32">
                {m.type === 'video' ? <video src={getMediaUrl(m.key)} className="w-full h-full object-cover" controls /> : <img src={getMediaUrl(m.key)} className="w-full h-full object-cover" />}
                <div className="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition z-10">
                  <button onClick={() => handleDownload(m.key, m.type)} className="bg-blue-500 text-white w-6 h-6 flex items-center justify-center rounded">📥</button>
                  <button onClick={() => handleDeleteFromLib(m.id)} className="bg-red-500 text-white w-6 h-6 flex items-center justify-center rounded">✕</button>
                </div>
              </div>
            ))}
            {mediaLib.length === 0 && <div className="col-span-full text-center py-10 text-gray-500">Библиотека пуста</div>}
          </div>
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="max-w-2xl mx-auto">
          <div className="bg-white p-6 rounded-lg shadow mb-8">
            <h2 className="text-xl font-bold mb-4">🤖 Настройки ИИ (Google Gemini)</h2>
            <p className="text-sm text-gray-500 mb-4">
              Введите ваш Gemini API Key. Его можно получить бесплатно в{' '}
              <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline font-medium">
                Google AI Studio
              </a>.
            </p>
            <div className="flex flex-col gap-3">
              <input type="text" placeholder="AIzaSy..." className="w-full p-3 border rounded-lg font-mono text-sm" value={geminiKey} onChange={e => setGeminiKey(e.target.value)} />
              <div className="flex flex-col sm:flex-row gap-2">
                <button onClick={handleSaveGemini} className="w-full sm:w-auto bg-blue-600 text-white px-4 py-2 rounded font-bold text-sm">Сохранить ключ</button>
                <button onClick={handleTestGemini} disabled={geminiTesting} className="w-full sm:w-auto bg-gray-600 text-white px-4 py-2 rounded font-bold text-sm disabled:opacity-50">{geminiTesting ? 'Проверка...' : 'Проверить ключ'}</button>
              </div>
              {geminiStatus && <div className={`p-3 rounded text-sm ${geminiStatus.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>{geminiStatus.type === 'success' ? '✅ ' : '❌ '} {geminiStatus.msg}</div>}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'licenses' && isOwner && viewAs === 'owner' && (
        <div>
          <div className="bg-white p-4 sm:p-6 rounded-lg shadow mb-8">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
              <h2 className="text-xl font-bold">Выдать новую лицензию</h2>
              <button onClick={downloadZip} className="w-full sm:w-auto text-center bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded shadow font-bold text-sm flex items-center justify-center gap-2 transition">📦 Скачать ZIP</button>
            </div>
            <form onSubmit={handleCreateLicense} className="flex flex-col sm:flex-row flex-wrap gap-4 items-start sm:items-end">
              <div className="flex-grow w-full sm:w-auto">
                <label className="block text-xs font-bold text-gray-600 mb-1">Имя клиента / Канал</label>
                <input type="text" className="w-full p-2 border rounded" value={newLicClient} onChange={e => setNewLicClient(e.target.value)} required />
              </div>
              <div className="w-full sm:w-auto">
                <label className="block text-xs font-bold text-gray-600 mb-1">Тариф</label>
                <select className="w-full sm:w-auto p-2 border rounded" value={newLicPlan} onChange={e => setNewLicPlan(e.target.value)}>
                  <option value="free">Free</option><option value="pro">Pro</option><option value="business">Business</option>
                </select>
              </div>
              <div className="w-full sm:w-auto">
                <label className="block text-xs font-bold text-gray-600 mb-1">Дней</label>
                <input type="number" className="w-full sm:w-24 p-2 border rounded" value={newLicDays} onChange={e => setNewLicDays(e.target.value)} required />
              </div>
              <button type="submit" disabled={generatingLic} className="w-full sm:w-auto bg-purple-600 text-white px-6 py-2 rounded font-bold disabled:opacity-50 h-[42px]">{generatingLic ? 'Генерация...' : 'Сгенерировать'}</button>
            </form>
          </div>

          {generatedKey && (
            <div className="bg-indigo-50 p-4 sm:p-6 rounded-lg shadow mb-8 border border-indigo-200">
              <h3 className="text-lg font-bold text-indigo-900 mb-2">✅ Лицензия создана!</h3>
              <div className="flex flex-col sm:flex-row gap-2 mb-4">
                <input type="text" readOnly value={generatedKey} className="w-full p-2 border rounded font-mono text-xs bg-white" />
                <button onClick={() => copyToClipboard(generatedKey)} className="w-full sm:w-auto bg-indigo-600 text-white px-4 py-2 rounded text-sm">Копировать</button>
              </div>
            </div>
          )}

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <h2 className="text-xl font-bold p-4 border-b">Выданные лицензии</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left min-w-[600px]">
                <thead><tr className="bg-gray-50 text-sm"><th className="p-4">Клиент</th><th className="p-4 text-center">Тариф</th><th className="p-4 text-center">Действует до</th><th className="p-4 text-center">Статус</th><th className="p-4 text-right">Действия</th></tr></thead>
                <tbody>
                  {licenses.map(l => (
                    <tr key={l.id} className="border-b last:border-0 hover:bg-gray-50 text-sm">
                      <td className="p-4 font-bold">{l.client_name}</td>
                      <td className="p-4 text-center uppercase text-xs font-bold text-indigo-600">{l.plan}</td>
                      <td className="p-4 text-center">{new Date(l.expires_at).toLocaleDateString('ru')}</td>
                      <td className="p-4 text-center"><span className={`px-2 py-1 rounded text-xs font-bold ${l.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{l.is_active ? 'Активна' : 'Отключена'}</span></td>
                      <td className="p-4 text-right flex justify-end gap-2">
                        <button onClick={() => copyToClipboard(l.license_key)} className="text-blue-600 hover:underline">Копировать</button>
                        <button onClick={() => handleToggleLicense(l.id)} className="text-orange-500 hover:underline">{l.is_active ? 'Отключить' : 'Включить'}</button>
                        <button onClick={() => handleDeleteLicense(l.id)} className="text-red-500 hover:underline">Удалить</button>
                      </td>
                    </tr>
                  ))}
                  {licenses.length === 0 && <tr><td colSpan="5" className="p-10 text-center text-gray-500">Вы еще не выдавали лицензии</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'trash' && (
        <div>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
            <h2 className="text-xl font-bold text-gray-700">Удаленные посты</h2>
            {trashPosts.length > 0 && <button onClick={handleEmptyTrash} className="w-full sm:w-auto bg-red-600 text-white px-4 py-2 rounded shadow text-sm font-bold">🗑 Очистить корзину</button>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trashPosts.map(post => (
              <div key={post.id} className="bg-gray-50 rounded-lg shadow-sm border border-gray-200 overflow-hidden flex flex-col opacity-80">
                {post.media_count > 0 ? (
                  <div className="h-48 bg-gray-200 relative grayscale">{post.media[0].type === 'video' ? <video src={getMediaUrl(post.media[0].key)} className="w-full h-full object-cover" controls /> : <img src={getMediaUrl(post.media[0].key)} className="w-full h-full object-cover" />}</div>
                ) : <div className="h-24 bg-gray-100 flex items-center justify-center text-gray-400">Без медиа</div>}
                <div className="p-4 flex-grow flex flex-col">
                  <div className="flex justify-between items-center mb-2"><span className="text-sm font-medium text-gray-500">@{post.source}</span><span className={`text-xs px-2 py-1 rounded-full font-bold uppercase bg-red-100 text-red-800`}>DELETED</span></div>
                  <p className="text-gray-600 text-sm flex-grow line-clamp-4 whitespace-pre-wrap">{post.text || 'Без текста'}</p>
                  <div className="mt-4 flex gap-2">
                    <button onClick={() => handleAction(post.id, 'restore')} className="flex-1 bg-green-500 text-white py-2 rounded text-sm">♻️ Восстановить</button>
                    <button onClick={() => handleAction(post.id, 'purge')} className="flex-1 bg-gray-600 text-white py-2 rounded text-sm">❌ Удалить</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'sources' && (
        <div className="max-w-5xl mx-auto">
          <div className="bg-white p-4 sm:p-6 rounded-lg shadow mb-8">
            <h2 className="text-xl font-bold mb-4">Добавить канал</h2>
            <div className="bg-blue-50 text-blue-800 p-4 rounded-lg mb-4 text-sm"><p className="font-bold mb-1">💡 Как добавить приватный канал?</p><p>Перешли любое сообщение из этого канала в чат с ботом <b>@tel_forw_bot</b>.</p></div>
            <form onSubmit={handleAddSource} className="flex flex-col sm:flex-row gap-2">
              <input type="text" placeholder="@channel_name или -100..." className="w-full sm:flex-grow p-3 border rounded-lg outline-none" value={newSourceInput} onChange={e => setNewSourceInput(e.target.value)} disabled={addingSource || sourcesLimitReached} />
              <button type="submit" disabled={addingSource || sourcesLimitReached} className="w-full sm:w-auto bg-blue-600 text-white px-6 py-3 rounded-lg font-bold disabled:opacity-50">Добавить</button>
            </form>
            {sourcesLimitReached && <p className="text-red-500 text-sm mt-2 font-medium">Достигнут лимит источников для тарифа '{license?.plan}' ({maxSources}).</p>}
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <h2 className="text-xl font-bold p-4 border-b">Активные источники</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left min-w-[800px]">
                <thead><tr className="bg-gray-50 text-sm"><th className="p-4">Название</th><th className="p-4 text-center">Статус</th><th className="p-4 text-center">Авто-публикация</th><th className="p-4 text-center">Цепочка / Шаблоны</th><th className="p-4 text-right">Действия</th></tr></thead>
                <tbody>
                  {sources.map(src => (
                    <tr key={src.id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="p-4"><div className="font-bold">{src.title}</div><div className="text-sm text-gray-500">@{src.username}</div></td>
                      <td className="p-4 text-center"><button onClick={() => handleToggleSource(src.id)} className={`px-3 py-1 rounded-full text-xs font-bold ${src.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-600'}`}>{src.enabled ? 'Активен' : 'Отключен'}</button></td>
                      <td className="p-4 text-center">
                        <div className="flex flex-col items-center gap-1">
                          <input type="checkbox" checked={src.auto_publish || false} onChange={(e) => handleToggleAutoPublish(src, e.target.checked)} className="w-5 h-5 cursor-pointer accent-indigo-600" />
                          {src.auto_publish && <select value={src.auto_template_id || ""} onChange={(e) => handleSetAutoTemplate(src, e.target.value)} className="text-xs p-1 border rounded w-full mt-1"><option value="">-- Без шаблона --</option>{templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select>}
                        </div>
                      </td>
                      <td className="p-4 text-center flex justify-center gap-2">
                        <button onClick={() => setEditingSource(src)} className="text-blue-600 text-sm font-medium hover:underline">📎 ({src.templates?.length || 0})</button>
                        <button onClick={() => openPipeline(src)} className={`text-sm font-medium hover:underline ${src.pipeline_json ? 'text-purple-600 font-bold' : 'text-gray-500'}`}>🧠 Цепочка</button>
                      </td>
                      <td className="p-4 text-right"><button onClick={() => handleDeleteSource(src.id)} className="text-red-500 text-sm font-medium">Удалить</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'templates' && (
        <div className="flex flex-col lg:flex-row gap-6">
          <div className="w-full lg:w-1/4 bg-white p-4 rounded shadow h-fit">
            <h2 className="text-lg font-bold mb-4">Папки</h2>
            <ul className="mb-4 space-y-1">
              <li><button onClick={() => setActiveFolder(null)} className={`w-full text-left px-3 py-2 rounded ${activeFolder === null ? 'bg-blue-100 font-bold text-blue-800' : 'hover:bg-gray-100'}`}>Все шаблоны</button></li>
              {folders.map(f => <li key={f.id} className="flex justify-between items-center group"><button onClick={() => setActiveFolder(f.id)} className={`flex-grow text-left px-3 py-2 rounded ${activeFolder === f.id ? 'bg-blue-100 font-bold text-blue-800' : 'hover:bg-gray-100'}`}>📁 {f.name}</button><button onClick={() => handleDeleteFolder(f.id)} className="text-red-400 opacity-0 group-hover:opacity-100 px-2">✕</button></li>)}
            </ul>
            <form onSubmit={handleCreateFolder} className="flex gap-1"><input placeholder="Новая папка" className="border p-1 text-sm rounded w-full" value={newFolderName} onChange={e => setNewFolderName(e.target.value)} /><button type="submit" className="bg-gray-200 px-3 rounded text-sm font-bold">+</button></form>
          </div>
          <div className="w-full lg:w-3/4 flex flex-col xl:flex-row gap-6">
            <div className="w-full xl:w-1/2">
              <h2 className="text-lg font-bold mb-4">Создать шаблон</h2>
              <form onSubmit={handleCreateTemplate} className="bg-white p-4 rounded shadow flex flex-col gap-3">
                <input placeholder="Название" className="p-2 border rounded" value={newTemplate.name} onChange={e => setNewTemplate({...newTemplate, name: e.target.value})} required />
                <textarea placeholder="Текст" className="p-2 border rounded h-24" value={newTemplate.text} onChange={e => setNewTemplate({...newTemplate, text: e.target.value})} />
                <select className="p-2 border rounded" value={newTemplate.attach_mode} onChange={e => setNewTemplate({...newTemplate, attach_mode: e.target.value})}><option value="append">В конец</option><option value="prepend">В начало</option><option value="standalone">Отдельное</option></select>
                <select className="p-2 border rounded" value={newTemplate.folder_id} onChange={e => setNewTemplate({...newTemplate, folder_id: e.target.value})}><option value="">-- Без папки --</option>{folders.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
                <div className="border-t pt-3 mt-1"><label className="block text-xs font-bold text-gray-600 mb-1">Медиа шаблона</label><input type="file" onChange={handleUploadTemplateMedia} disabled={tplUploading} className="block w-full text-xs" /></div>
                <button type="submit" className="bg-blue-600 text-white py-2 rounded font-bold mt-2">Создать</button>
              </form>
            </div>
            <div className="w-full xl:w-1/2">
              <h2 className="text-lg font-bold mb-4">{activeFolder ? folders.find(f => f.id === activeFolder)?.name : "Все шаблоны"}</h2>
              <div className="flex flex-col gap-3 max-h-[60vh] overflow-y-auto pr-2">
                {filteredTemplates.map(t => (
                  <div key={t.id} className="bg-white p-3 rounded shadow flex flex-col justify-between">
                    <div className="flex justify-between items-start">
                      <div><h3 className="font-bold">{t.name}</h3><p className="text-sm text-gray-600 mt-1 whitespace-pre-wrap">{t.text}</p></div>
                      <div className="flex gap-2"><button onClick={() => openEditTemplate(t)} className="text-blue-500 text-sm font-medium">✏️</button><button onClick={() => handleDeleteTemplate(t.id)} className="text-red-500 text-sm font-medium">Удалить</button></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'metrics' && metrics && (
        <div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white p-6 rounded-lg shadow border-t-4 border-blue-500"><p className="text-gray-500 text-sm font-bold uppercase">Всего</p><p className="text-4xl font-bold text-gray-800 mt-2">{metrics.summary.total}</p></div>
            <div className="bg-white p-6 rounded-lg shadow border-t-4 border-green-500"><p className="text-gray-500 text-sm font-bold uppercase">Опубликовано</p><p className="text-4xl font-bold text-green-600 mt-2">{metrics.summary.published}</p></div>
            <div className="bg-white p-6 rounded-lg shadow border-t-4 border-red-500"><p className="text-gray-500 text-sm font-bold uppercase">Удалено</p><p className="text-4xl font-bold text-red-600 mt-2">{metrics.summary.deleted}</p></div>
            <div className="bg-white p-6 rounded-lg shadow border-t-4 border-yellow-500"><p className="text-gray-500 text-sm font-bold uppercase">В очереди</p><p className="text-4xl font-bold text-yellow-600 mt-2">{metrics.summary.pending}</p></div>
          </div>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
            <h2 className="text-2xl font-bold">Эффективность источников</h2>
            <button onClick={handleClearChannel} disabled={clearing} className="w-full sm:w-auto bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded shadow text-sm font-bold disabled:opacity-50">{clearing ? 'Очистка...' : '🧹 Очистить канал'}</button>
          </div>
          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[600px]">
              <thead><tr className="bg-gray-100 text-gray-600 text-sm uppercase"><th className="p-4 border-b">Канал</th><th className="p-4 border-b text-center">Всего</th><th className="p-4 border-b text-center text-green-600">Опубл.</th><th className="p-4 border-b text-center text-red-600">Удалено</th><th className="p-4 border-b text-center">КПД</th></tr></thead>
              <tbody>{metrics.sources.map((src, idx) => (<tr key={idx} className="hover:bg-gray-50 border-b last:border-0"><td className="p-4 font-medium">{src.source === '@manual' ? '✍️ Ручные' : src.source}</td><td className="p-4 text-center">{src.total}</td><td className="p-4 text-center font-bold text-green-600">{src.published}</td><td className="p-4 text-center font-bold text-red-600">{src.deleted}</td><td className="p-4 text-center"><div className="flex items-center justify-center gap-2"><span className="font-bold text-lg w-12">{src.efficiency}%</span><div className="w-16 sm:w-32 bg-gray-200 rounded-full h-2.5"><div className={`h-2.5 rounded-full ${src.efficiency > 70 ? 'bg-green-500' : src.efficiency > 40 ? 'bg-yellow-400' : 'bg-red-500'}`} style={{ width: `${src.efficiency}%` }}></div></div></div></td></tr>))}</tbody>
            </table>
          </div>
        </div>
      )}

      {/* МОДАЛКА РЕДАКТОРА ПОСТА */}
      <Modal isOpen={!!editingPost} onClose={closeEditor} title={`Пост #${editingPost?.id}`} maxWidth="max-w-3xl">
        <div className="flex flex-col gap-4">
          <div>
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-2 gap-2">
              <label className="text-sm font-bold text-gray-700">Медиа ({editingPost?.media?.length || 0})</label>
              <div className="flex gap-2">
                <button onClick={() => handleRefetch(editingPost.id)} disabled={refetching} className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-lg font-bold transition disabled:opacity-50">{refetching ? '...' : '🔄 Заново'}</button>
                <button onClick={() => setShowLibSelector(true)} className="text-xs bg-purple-100 hover:bg-purple-200 text-purple-700 px-3 py-1.5 rounded-lg font-bold transition">📁 Из библиотеки</button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {editingPost?.media?.map(m => (
                <div key={m.id} className="relative w-20 h-20 border rounded-lg group bg-gray-100 overflow-hidden">
                  {m.type === 'video' ? <video src={getMediaUrl(m.key)} className="w-full h-full object-cover" controls /> : <img src={getMediaUrl(m.key)} className="w-full h-full object-cover" />}
                  <div className="absolute top-1 right-1 flex opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition z-10">
                    <button onClick={() => handleDeleteMedia(m.id)} className="bg-red-500/90 hover:bg-red-600 text-white w-6 h-6 flex items-center justify-center text-xs rounded-md shadow">✕</button>
                  </div>
                </div>
              ))}
            </div>
            <input type="file" onChange={handleUploadMedia} disabled={uploading} className="mt-2 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
          </div>

          <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
            <label className="block text-sm font-bold text-purple-800 mb-2">📎 Шаблоны поста</label>
            <div className="flex flex-col gap-2 mb-2">
              {editingPost?.templates?.map(t => (
                <div key={t.id} className="flex justify-between items-center bg-white p-2 rounded shadow-sm text-sm">
                  <span>{t.name} ({t.mode})</span>
                  <button onClick={() => handleDetachTemplate(t.id)} className="text-red-500 font-bold px-2">&times;</button>
                </div>
              ))}
            </div>
            <div className="flex gap-2 flex-col sm:flex-row">
              <select className="border rounded-lg p-2 text-sm flex-grow outline-none focus:ring-2 focus:ring-purple-500" value={selectedTemplate} onChange={e => setSelectedTemplate(e.target.value)}><option value="">-- Выбрать --</option>{templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
              <button onClick={handleAttachTemplate} className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-bold w-full sm:w-auto transition">+ Добавить</button>
            </div>
          </div>

          <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200">
            <label className="block text-sm font-bold text-emerald-800 mb-2">🎨 Генерация картинки</label>
            <div className="flex flex-wrap gap-2 mb-2">
              <select value={imageModel} onChange={e => setImageModel(e.target.value)} className="border rounded-lg p-1.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500">{imageModels.map(m => <option key={m} value={m}>{m}</option>)}</select>
              <select value={`${imageWidth}x${imageHeight}`} onChange={e => { const [w, h] = e.target.value.split('x').map(Number); setImageWidth(w); setImageHeight(h); }} className="border rounded-lg p-1.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500">
                <option value="1080x1080">Квадрат 1080×1080</option><option value="1080x1350">Портрет 1080×1350</option><option value="1920x1080">Альбом 1920×1080</option>
              </select>
              <input type="number" placeholder="Seed" className="border rounded-lg p-1.5 text-sm w-28 outline-none focus:ring-2 focus:ring-emerald-500" value={imageSeed} onChange={e => setImageSeed(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <input placeholder="Промпт для картинки..." className="flex-grow p-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-emerald-500" value={imagePrompt} onChange={e => setImagePrompt(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !imageGenerating) { e.preventDefault(); handleGenerateImage(); } }} disabled={imageGenerating} />
              <button onClick={() => handleGenerateImage()} disabled={imageGenerating} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-bold disabled:opacity-50 transition shadow whitespace-nowrap">{imageGenerating ? 'Генерация...' : '🎨 Сгенерировать'}</button>
            </div>
            {lastGeneratedMediaId && editingPost.media?.find(m => m.id === lastGeneratedMediaId) && (
              <div className="mt-3 flex items-center gap-3 bg-white p-2 rounded-lg border shadow-sm">
                <img src={getMediaUrl(editingPost.media.find(m => m.id === lastGeneratedMediaId).key)} className="w-12 h-12 object-cover rounded-md" />
                <span className="text-xs text-gray-600 flex-grow">Сгенерировано</span>
                <button onClick={() => handleGenerateImage(imagePrompt, lastGeneratedMediaId)} disabled={imageGenerating} className="text-xs bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-md disabled:opacity-50 font-bold transition shadow-sm">🔄 Заменить</button>
              </div>
            )}
          </div>

          <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
            <label className="block text-sm font-bold text-blue-800 mb-2">🔗 Кнопки под постом</label>
            {postButtons.map((btn, idx) => (
              <div key={idx} className="flex gap-2 mb-2">
                <input placeholder="Текст кнопки" className="p-2 border rounded-lg text-sm w-1/3 outline-none focus:ring-2 focus:ring-blue-500" value={btn.text} onChange={e => { const nb = [...postButtons]; nb[idx].text = e.target.value; setPostButtons(nb); }} />
                <input placeholder="https://ссылка" className="p-2 border rounded-lg text-sm flex-grow outline-none focus:ring-2 focus:ring-blue-500" value={btn.url} onChange={e => { const nb = [...postButtons]; nb[idx].url = e.target.value; setPostButtons(nb); }} />
                <button onClick={() => setPostButtons(postButtons.filter((_, i) => i !== idx))} className="text-red-500 font-bold px-2 hover:bg-red-50 rounded-lg transition">&times;</button>
              </div>
            ))}
            <button onClick={() => setPostButtons([...postButtons, { text: "", url: "" }])} className="text-sm bg-blue-100 hover:bg-blue-200 text-blue-700 px-4 py-1.5 rounded-lg font-bold mt-1 transition">+ Добавить кнопку</button>
          </div>

          <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
            <div className="flex justify-between items-center mb-3">
              <label className="block text-sm font-bold text-gray-700">🤖 Помощник ИИ</label>
              <button onClick={handleRunPipeline} disabled={runningPipeline} className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg font-bold disabled:opacity-50 transition shadow">🧠 Прогнать цепочку</button>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-2 mb-3">
              <input placeholder="Задание для ИИ (например, 'Напиши пост про ...')" className="flex-grow p-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-pink-500" value={aiPrompt} onChange={e => setAiPrompt(e.target.value)} />
              <button onClick={handleGenerateText} disabled={aiGenerating} className="w-full sm:w-auto bg-pink-600 hover:bg-pink-700 text-white px-4 py-2 rounded-lg text-sm font-bold disabled:opacity-50 transition shadow">{aiGenerating ? '...' : '✨ Написать с ИИ'}</button>
            </div>
            
            <div className="flex flex-wrap gap-2">
              <button onClick={handleTranslate} disabled={aiLoading} className="flex-grow sm:flex-grow-0 bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-bold disabled:opacity-50 transition shadow">🇷🇺 Перевести</button>
              <div className="flex items-center gap-1 bg-white border rounded-lg px-2 py-1 flex-grow sm:flex-grow-0 focus-within:ring-2 focus-within:ring-indigo-500">
                <input type="number" placeholder="Слов" className="w-16 outline-none text-sm bg-transparent" value={wordCount} onChange={e => setWordCount(e.target.value)} />
                <button onClick={handleRewrite} disabled={aiLoading} className="bg-indigo-500 hover:bg-indigo-600 text-white px-3 py-1 rounded-md text-sm font-bold disabled:opacity-50 transition">🔄 Рерайт</button>
              </div>
              <button onClick={handleClearLinks} disabled={linkClearing} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-bold disabled:opacity-50 transition shadow">{linkClearing ? '...' : '🧹 Очистить ссылки'}</button>
              {aiLoading && <span className="text-sm text-indigo-600 animate-pulse flex items-center ml-auto">Нейросеть думает...</span>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-700 mb-1">Текст поста</label>
            <RichTextEditor value={editText} onChange={setEditText} />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            <button onClick={closeEditor} className="px-6 py-2 text-gray-600 font-medium hover:bg-gray-100 rounded-lg transition">Отмена</button>
            <button onClick={saveEdit} className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold shadow transition">Сохранить</button>
          </div>
        </div>
      </Modal>

      {/* МОДАЛКА НАСТРОЙКИ ЦЕПОЧКИ */}
      <Modal isOpen={!!pipelineSource} onClose={() => setPipelineSource(null)} title={`Цепочка: ${pipelineSource?.title}`}>
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-500 bg-gray-50 p-3 rounded-lg border">Эти шаги будут выполняться по порядку при появлении нового поста из этого источника.</p>
          
          <div className="flex flex-col gap-3">
            {pipelineSteps.map((step, idx) => (
              <div key={idx} className="flex flex-col gap-3 bg-white p-4 rounded-xl border border-gray-200 shadow-sm relative">
                <div className="flex items-center gap-3">
                  <span className="font-bold text-gray-400 w-6 text-center">{idx + 1}</span>
                  <select className="border rounded-lg p-2 text-sm font-bold flex-grow outline-none focus:ring-2 focus:ring-purple-500" value={step.type} onChange={e => updatePipelineStep(idx, 'type', e.target.value)}>
                    <option value="remove_links">🧹 Очистить ссылки</option>
                    <option value="rewrite">🔄 Рерайт</option>
                    <option value="translate">🇷🇺 Перевод</option>
                    <option value="generate_text">✨ Написать с ИИ</option>
                    <option value="generate_image">🎨 Сгенерировать картинку</option>
                  </select>
                  <div className="flex gap-1">
                    <button onClick={() => movePipelineStep(idx, 'up')} disabled={idx === 0} className="text-gray-400 hover:text-gray-700 disabled:opacity-30 p-1">⬆️</button>
                    <button onClick={() => movePipelineStep(idx, 'down')} disabled={idx === pipelineSteps.length - 1} className="text-gray-400 hover:text-gray-700 disabled:opacity-30 p-1">⬇️</button>
                    <button onClick={() => setPipelineSteps(pipelineSteps.filter((_, i) => i !== idx))} className="text-red-400 hover:text-red-600 p-1 ml-2 font-bold">&times;</button>
                  </div>
                </div>
                
                {step.type === 'rewrite' && (
                  <div className="ml-9 flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-600">Слов:</span>
                    <input type="number" className="border rounded-lg p-1.5 text-sm w-24 outline-none focus:ring-2 focus:ring-purple-500" value={step.params.words || 30} onChange={e => updatePipelineStep(idx, 'words', parseInt(e.target.value))} />
                  </div>
                )}
                {step.type === 'generate_text' && (
                  <div className="ml-9">
                    <input type="text" className="border rounded-lg p-2 text-sm w-full outline-none focus:ring-2 focus:ring-purple-500" placeholder="Инструкция для ИИ (например: 'Сделай текст короче')..." value={step.params.prompt || ""} onChange={e => updatePipelineStep(idx, 'prompt', e.target.value)} />
                  </div>
                )}
                {step.type === 'generate_image' && (
                  <div className="ml-9 flex flex-col sm:flex-row gap-2">
                    <input type="text" className="border rounded-lg p-2 text-sm flex-grow outline-none focus:ring-2 focus:ring-purple-500" placeholder="Промпт картинки..." value={step.params.prompt || ""} onChange={e => updatePipelineStep(idx, 'prompt', e.target.value)} />
                    <div className="flex gap-2">
                      <input type="number" className="border rounded-lg p-2 text-sm w-20 outline-none focus:ring-2 focus:ring-purple-500" placeholder="Ширина" value={step.params.width || 1080} onChange={e => updatePipelineStep(idx, 'width', parseInt(e.target.value))} />
                      <input type="number" className="border rounded-lg p-2 text-sm w-20 outline-none focus:ring-2 focus:ring-purple-500" placeholder="Высота" value={step.params.height || 1080} onChange={e => updatePipelineStep(idx, 'height', parseInt(e.target.value))} />
                    </div>
                  </div>
                )}
              </div>
            ))}
            {pipelineSteps.length === 0 && <div className="text-center text-gray-400 py-8 bg-gray-50 rounded-xl border border-dashed">Цепочка пуста (посты будут приходить как есть)</div>}
          </div>

          <div className="flex flex-col sm:flex-row gap-2 border-t pt-4 mt-2">
            <select id="addStepSelect" className="border rounded-lg p-2 text-sm flex-grow outline-none focus:ring-2 focus:ring-purple-500">
              <option value="remove_links">🧹 Очистить ссылки</option>
              <option value="rewrite">🔄 Рерайт</option>
              <option value="translate">🇷🇺 Перевод</option>
              <option value="generate_text">✨ Написать с ИИ</option>
              <option value="generate_image">🎨 Сгенерировать картинку</option>
            </select>
            <button onClick={() => { const sel = document.getElementById('addStepSelect'); addPipelineStep(sel.value); }} className="w-full sm:w-auto bg-gray-800 hover:bg-gray-900 text-white px-6 py-2 rounded-lg text-sm font-bold transition shadow">+ Добавить шаг</button>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 mt-2">
            <button onClick={() => setPipelineSource(null)} className="px-6 py-2 text-gray-600 font-medium hover:bg-gray-100 rounded-lg transition">Отмена</button>
            <button onClick={savePipeline} disabled={savingPipeline} className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-bold shadow transition disabled:opacity-50">{savingPipeline ? 'Сохранение...' : 'Сохранить цепочку'}</button>
          </div>
        </div>
      </Modal>

      {/* ОСТАЛЬНЫЕ МОДАЛКИ */}
      <Modal isOpen={showLibSelector && !!editingPost} onClose={() => setShowLibSelector(false)} title="Выбрать из библиотеки" maxWidth="max-w-4xl">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {mediaLib.map(m => (
            <div key={m.id} onClick={() => handleAttachFromLib(m.id)} className="cursor-pointer border rounded-xl overflow-hidden hover:ring-4 hover:ring-blue-100 transition-all group relative h-32 bg-gray-100">
              {m.type === 'video' ? <video src={getMediaUrl(m.key)} className="w-full h-full object-cover" controls /> : <img src={getMediaUrl(m.key)} className="w-full h-full object-cover" />}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 flex items-center justify-center transition z-0">
                <span className="text-white opacity-0 group-hover:opacity-100 font-bold text-lg">+ Добавить</span>
              </div>
            </div>
          ))}
          {mediaLib.length === 0 && <div className="col-span-full text-center py-10 text-gray-500">Библиотека пуста</div>}
        </div>
      </Modal>

      <Modal isOpen={!!editingSource} onClose={() => setEditingSource(null)} title={`Шаблоны для ${editingSource?.title}`} maxWidth="max-w-lg">
        <p className="text-sm text-gray-500 mb-4 bg-gray-50 p-3 rounded-lg border">Эти шаблоны будут отправляться <b>отдельными сообщениями</b> после публикации.</p>
        <div className="flex flex-col gap-2 mb-4">
          {editingSource?.templates?.map(t => (
            <div key={t.id} className="flex justify-between items-center bg-white p-2 rounded-lg shadow-sm text-sm border">
              <span className="font-medium">📎 {t.name}</span>
              <button onClick={() => handleDetachSourceTemplate(t.id)} className="text-red-500 font-bold px-2 hover:bg-red-50 rounded transition">&times;</button>
            </div>
          ))}
        </div>
        <div className="flex gap-2 border-t pt-4">
          <select className="border rounded-lg p-2 text-sm flex-grow outline-none focus:ring-2 focus:ring-blue-500" value={sourceTemplateId} onChange={e => setSourceTemplateId(e.target.value)}><option value="">-- Выбрать шаблон --</option>{templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
          <button onClick={handleAttachSourceTemplate} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-bold shadow transition">Прикрепить</button>
        </div>
      </Modal>

      <Modal isOpen={!!editingTemplate && !!editTemplateData} onClose={closeEditTemplate} title={`Редактирование: ${editingTemplate?.name}`} maxWidth="max-w-2xl">
        <form id="editTemplateForm" onSubmit={handleUpdateTemplate} className="flex flex-col gap-4">
          <input placeholder="Название" className="p-2.5 border rounded-lg outline-none focus:ring-2 focus:ring-blue-500" value={editTemplateData?.name || ''} onChange={e => setEditTemplateData({...editTemplateData, name: e.target.value})} required />
          <textarea placeholder="Текст" className="p-2.5 border rounded-lg h-32 outline-none focus:ring-2 focus:ring-blue-500" value={editTemplateData?.text || ''} onChange={e => setEditTemplateData({...editTemplateData, text: e.target.value})} />
          <div className="flex gap-4">
            <select className="p-2.5 border rounded-lg flex-1 outline-none focus:ring-2 focus:ring-blue-500" value={editTemplateData?.attach_mode || 'append'} onChange={e => setEditTemplateData({...editTemplateData, attach_mode: e.target.value})}><option value="append">В конец</option><option value="prepend">В начало</option><option value="standalone">Отдельное</option></select>
            <select className="p-2.5 border rounded-lg flex-1 outline-none focus:ring-2 focus:ring-blue-500" value={editTemplateData?.folder_id || ''} onChange={e => setEditTemplateData({...editTemplateData, folder_id: e.target.value})}><option value="">-- Без папки --</option>{folders.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
          </div>
          
          <div className="border-t pt-4 mt-2">
            <label className="block text-sm font-bold text-gray-700 mb-2">Медиа шаблона</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {editTemplateData?.media_json?.map((m, i) => (
                <div key={i} className="relative w-16 h-16 border rounded-lg group bg-gray-100 overflow-hidden">
                  {m.type === 'video' ? <video src={getMediaUrl(m.key)} className="w-full h-full object-cover" /> : <img src={getMediaUrl(m.key)} className="w-full h-full object-cover" />}
                  <button type="button" onClick={() => removeEditTemplateMedia(i)} className="absolute top-1 right-1 bg-red-500 text-white w-5 h-5 flex items-center justify-center text-[10px] rounded shadow">✕</button>
                </div>
              ))}
            </div>
            <input type="file" onChange={handleUploadEditTemplateMedia} disabled={editTplUploading} className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
          </div>

          <div className="border-t pt-4 mt-2">
            <label className="block text-sm font-bold text-gray-700 mb-2">🔗 Кнопки шаблона</label>
            {editTemplateData?.buttons_json?.map((btn, idx) => (
              <div key={idx} className="flex gap-2 mb-2">
                <input placeholder="Текст" className="p-2 border rounded-lg text-sm w-1/3 outline-none focus:ring-2 focus:ring-blue-500" value={btn.text} onChange={e => updateEditTemplateButton(idx, 'text', e.target.value)} />
                <input placeholder="https://..." className="p-2 border rounded-lg text-sm flex-grow outline-none focus:ring-2 focus:ring-blue-500" value={btn.url} onChange={e => updateEditTemplateButton(idx, 'url', e.target.value)} />
                <button type="button" onClick={() => removeEditTemplateButton(idx)} className="text-red-500 font-bold px-2 hover:bg-red-50 rounded-lg transition">&times;</button>
              </div>
            ))}
            <button type="button" onClick={addEditTemplateButton} className="text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-1.5 rounded-lg font-bold transition mt-2">+ Кнопка</button>
          </div>
        </form>
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 mt-4">
          <button onClick={closeEditTemplate} className="px-6 py-2 text-gray-600 font-medium hover:bg-gray-100 rounded-lg transition">Отмена</button>
          <button type="submit" form="editTemplateForm" className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold shadow transition">Сохранить изменения</button>
        </div>
      </Modal>

      {/* КРАСИВАЯ МОДАЛКА АПГРЕЙДА */}
      <Modal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} title="Доступно на платных тарифах" maxWidth="max-w-md">
        <div className="text-center py-6">
          <div className="w-20 h-20 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4 shadow-inner">
            <span className="text-4xl">🚀</span>
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Функция «{upgradeFeature}»</h3>
          <p className="text-gray-500 mb-6 text-sm leading-relaxed">
            Эта возможность доступна только на тарифах <b>Pro</b> и <b>Business</b>. 
            Перейдите на платный тариф, чтобы снять все ограничения и использовать нейросети на полную мощность.
          </p>
          <div className="flex flex-col gap-2">
            <a href="https://t.me/osdal" target="_blank" rel="noreferrer" className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-bold py-3 rounded-xl shadow-lg transition transform hover:-translate-y-0.5">
              Связаться для покупки
            </a>
            <button onClick={() => setShowUpgradeModal(false)} className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold py-3 rounded-xl transition">
              Позже
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default App