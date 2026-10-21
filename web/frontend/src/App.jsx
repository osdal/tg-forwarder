import { useEffect, useState } from 'react'

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
  const [loading, setLoading] = useState(true)
  
  const [status, setStatus] = useState({ bot_online: false, collector_online: false })
  const [procStatus, setProcStatus] = useState({ bot: false, collector: false })
  
  const [queueSourceFilter, setQueueSourceFilter] = useState('all')

  const [editingPost, setEditingPost] = useState(null)
  const [editText, setEditText] = useState("")
  const [uploading, setUploading] = useState(false)
  const [attachMode, setAttachMode] = useState("append")
  const [selectedTemplate, setSelectedTemplate] = useState("")
  
  const [aiLoading, setAiLoading] = useState(false)
  const [linkClearing, setLinkClearing] = useState(false)
  const [aiPrompt, setAiPrompt] = useState("")
  const [aiGenerating, setAiGenerating] = useState(false)
  
  const [wordCount, setWordCount] = useState("")
  const [postButtons, setPostButtons] = useState([])
  
  const [showLibSelector, setShowLibSelector] = useState(false)
  const [libUploading, setLibUploading] = useState(false)
  const [refetching, setRefetching] = useState(false)
  const [cacheBuster, setCacheBuster] = useState(Date.now())
  const [clearing, setClearing] = useState(false)

  const [editingSource, setEditingSource] = useState(null)
  const [sourceTemplateId, setSourceTemplateId] = useState("")

  const [newTemplate, setNewTemplate] = useState({ name: "", text: "", attach_mode: "append", folder_id: "", media_json: [], buttons_json: [] })
  const [editingTemplate, setEditingTemplate] = useState(null)
  const [editTemplateData, setEditTemplateData] = useState(null)
  const [newFolderName, setNewFolderName] = useState("")
  const [activeFolder, setActiveFolder] = useState(null)
  const [tplUploading, setTplUploading] = useState(false)
  const [editTplUploading, setEditTplUploading] = useState(false)

  const [newSourceInput, setNewSourceInput] = useState("")
  const [addingSource, setAddingSource] = useState(false)

  const fetchWithAuth = async (url, options = {}) => {
    const headers = { ...options.headers, 'Authorization': `Bearer ${token}` }
    const res = await fetch(url, { ...options, headers })
    if (res.status === 401 || res.status === 403) {
      localStorage.removeItem('token'); setToken(null); throw new Error("Unauthorized")
    }
    return res
  }

  const fetchData = async () => {
    if (!token) return
    try {
      const [postsRes, trashRes, libRes, tplRes, foldRes, metRes, srcRes] = await Promise.all([
        fetchWithAuth('http://localhost:8000/api/posts?trash=false'),
        fetchWithAuth('http://localhost:8000/api/posts?trash=true'),
        fetchWithAuth('http://localhost:8000/api/media-library'),
        fetchWithAuth('http://localhost:8000/api/templates'),
        fetchWithAuth('http://localhost:8000/api/template-folders'),
        fetchWithAuth('http://localhost:8000/api/metrics'),
        fetchWithAuth('http://localhost:8000/api/sources')
      ])
      setPosts(await postsRes.json()); setTrashPosts(await trashRes.json());
      setMediaLib(await libRes.json()); setTemplates(await tplRes.json()); 
      setFolders(await foldRes.json()); setMetrics(await metRes.json()); setSources(await srcRes.json())
    } catch (err) { console.error(err) } finally { setLoading(false) }
  }

  const fetchStatus = async () => {
    if (!token) return
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/status')
      setStatus(await res.json())
      const procRes = await fetchWithAuth('http://localhost:8000/api/processes/status')
      setProcStatus(await procRes.json())
    } catch (err) {}
  }

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
    window.onTelegramAuth = async (user) => {
      try {
        const res = await fetch('http://localhost:8000/api/auth/telegram', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(user) })
        if (res.ok) { const data = await res.json(); localStorage.setItem('token', data.token); setToken(data.token) }
      } catch (e) { alert("Ошибка сети") }
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
      const res = await fetch('http://localhost:8000/api/auth/dev', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) })
      if (res.ok) { const data = await res.json(); localStorage.setItem('token', data.token); setToken(data.token) }
      else alert("Неверный пароль")
    } catch (err) { alert("Ошибка сети") }
  }

  const handleProcessAction = async (name, action) => {
    try {
      const res = await fetchWithAuth(`http://localhost:8000/api/processes/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      })
      if (res.ok) fetchStatus(); else { const err = await res.json(); alert(err.detail || "Ошибка") }
    } catch (err) { alert("Ошибка сети") }
  }

  const handleForceKillAll = async () => {
    if (!window.confirm("Убить ВСЕ процессы бота и коллектора? Это решит проблему 'Conflict'.")) return;
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/processes/force-kill-all', { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        alert(data.message)
        fetchStatus()
      }
    } catch (err) { alert("Ошибка") }
  }

  const handleClearChannel = async () => {
    if (!window.confirm("ВНИМАНИЕ! Это удалит ВСЕ сообщения из целевого Telegram-канала. Продолжить?")) return;
    setClearing(true);
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/target-channel/clear', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        alert(`✅ ${data.message}`);
      } else {
        alert(`❌ Ошибка: ${(await res.json()).detail}`);
      }
    } catch (err) {
      alert("Ошибка сети");
    } finally {
      setClearing(false);
    }
  }

  const handleAction = async (postId, action) => {
    try { 
      const method = action === 'purge' ? 'DELETE' : 'POST';
      if ((await fetchWithAuth(`http://localhost:8000/api/posts/${postId}/${action}`, { method })).ok) fetchData() 
    } catch (err) { alert("Ошибка") }
  }

  const handleEmptyTrash = async () => {
    if (!window.confirm("Удалить ВСЕ посты из корзины навсегда?")) return;
    if ((await fetchWithAuth(`http://localhost:8000/api/posts/trash/empty`, { method: 'DELETE' })).ok) fetchData();
  }

  const handleRefetch = async (postId) => {
    setRefetching(true);
    try {
      const res = await fetchWithAuth(`http://localhost:8000/api/posts/${postId}/refetch`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setCacheBuster(Date.now());
        alert(`✅ ${data.message}`);
        const single = await fetchWithAuth(`http://localhost:8000/api/posts/${postId}`).then(r => r.json());
        setEditingPost(single);
        fetchData();
      } else {
        const err = await res.json();
        alert(`❌ Ошибка: ${err.detail}`);
      }
    } catch (err) { alert("Ошибка сети"); }
    finally { setRefetching(false); }
  }

  const handleCreateManualPost = async () => {
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/manual-post', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        const newPost = await fetchWithAuth(`http://localhost:8000/api/posts/${data.id}`).then(r => r.json());
        setEditingPost(newPost);
        setEditText("");
        setPostButtons([]);
        setAiPrompt("");
        fetchData();
      } else {
        const err = await res.json();
        alert(`Ошибка создания поста: ${err.detail || "Неизвестная ошибка"}`);
      }
    } catch (err) { alert("Ошибка сети"); }
  }

  const saveEdit = async () => {
    try {
      await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ text: editText, buttons_json: postButtons.filter(b => b.text && b.url) })
      })
      closeEditor(); fetchData()
    } catch (err) { alert("Ошибка") }
  }

  const handleTranslate = async () => {
    if (!editText) return; setAiLoading(true)
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/ai/translate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: editText }) })
      if (res.ok) setEditText((await res.json()).result)
    } finally { setAiLoading(false) }
  }

  const handleRewrite = async () => {
    if (!editText) return; setAiLoading(true)
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/ai/rewrite', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: editText, word_count: wordCount ? parseInt(wordCount) : null }) })
      if (res.ok) setEditText((await res.json()).result)
    } finally { setAiLoading(false) }
  }

  const handleClearLinks = async () => {
    if (!editText) return; setLinkClearing(true)
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/ai/remove-links', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: editText }) })
      if (res.ok) setEditText((await res.json()).result)
    } finally { setLinkClearing(false) }
  }

  const handleGenerateText = async () => {
    if (!aiPrompt.trim()) return alert("Напиши задание для ИИ.");
    setAiGenerating(true);
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/ai/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: aiPrompt, base_text: editText })
      });
      if (res.ok) {
        const data = await res.json();
        setEditText(data.result);
      } else {
        const err = await res.json();
        alert(`Ошибка ИИ: ${err.detail}`);
      }
    } catch (err) {
      alert("Ошибка сети");
    } finally {
      setAiGenerating(false);
    }
  }

  const handleUploadMedia = async (e) => {
    const file = e.target.files[0]; if (!file) return
    setUploading(true); const formData = new FormData(); formData.append('file', file)
    try {
      await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}/media`, { method: 'POST', body: formData })
      setCacheBuster(Date.now());
      const updated = await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}`).then(r => r.json())
      setEditingPost(updated); fetchData()
    } finally { setUploading(false); e.target.value = null }
  }

  const handleDeleteMedia = async (mediaId) => {
    if (!window.confirm("Удалить медиа?")) return
    const res = await fetchWithAuth(`http://localhost:8000/api/media/${mediaId}`, { method: 'DELETE' })
    if (!res.ok) return alert("Ошибка удаления")
    const updated = await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}`).then(r => r.json())
    setEditingPost(updated); fetchData()
  }
  
  const handleSaveToLib = async (mediaId) => {
    try {
      const res = await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}/media/save-to-library/${mediaId}`, { method: 'POST' })
      if (res.ok) { fetchData(); alert("✅ Медиа сохранено в библиотеку!") }
      else { alert(`❌ Ошибка: ${(await res.json()).detail || "Не удалось сохранить"}`) }
    } catch (err) { alert("Ошибка сети при сохранении") }
  }

  const handleAttachFromLib = async (libId) => {
    const res = await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}/media/from-library/${libId}`, { method: 'POST' })
    if (!res.ok) return alert("Ошибка прикрепления медиа")
    setCacheBuster(Date.now());
    const updated = await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}`).then(r => r.json())
    setEditingPost(updated); setShowLibSelector(false); fetchData()
  }

  const handleUploadToLib = async (e) => {
    const file = e.target.files[0]; if (!file) return
    setLibUploading(true); const formData = new FormData(); formData.append('file', file)
    try {
      await fetchWithAuth('http://localhost:8000/api/media-library/upload', { method: 'POST', body: formData })
      setCacheBuster(Date.now());
      fetchData()
    } finally { setLibUploading(false); e.target.value = null }
  }

  const handleDeleteFromLib = async (libId) => {
    if (!window.confirm("Удалить файл из библиотеки навсегда?")) return
    await fetchWithAuth(`http://localhost:8000/api/media-library/${libId}`, { method: 'DELETE' })
    fetchData()
  }

  const handleDownload = async (key, type) => {
    try {
      const response = await fetch(`http://localhost:9000/media/${key}`);
      if (!response.ok) throw new Error("Ошибка скачивания");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = key.split('.').pop() || (type === 'video' ? 'mp4' : 'jpg');
      a.download = `media_${Date.now()}.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Не удалось скачать файл: " + err.message);
    }
  }

  const handleAttachTemplate = async () => {
    if (!selectedTemplate) return
    const res = await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}/templates`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ template_id: parseInt(selectedTemplate), mode: attachMode }) 
    })
    if (!res.ok) {
      const err = await res.json()
      return alert(`Ошибка прикрепления: ${err.detail}`)
    }
    const updatedRes = await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}`)
    if (!updatedRes.ok) return alert("Ошибка обновления данных")
    
    const updated = await updatedRes.json()
    setEditingPost(updated); fetchData(); setSelectedTemplate("")
  }

  const handleDetachTemplate = async (tplId) => {
    const res = await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}/templates/${tplId}`, { method: 'DELETE' })
    if (!res.ok) return alert("Ошибка открепления")
    const updated = await fetchWithAuth(`http://localhost:8000/api/posts/${editingPost.id}`).then(r => r.json())
    setEditingPost(updated); fetchData()
  }

  const handleAttachSourceTemplate = async () => {
    if (!sourceTemplateId) return
    await fetchWithAuth(`http://localhost:8000/api/sources/${editingSource.id}/templates`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ template_id: parseInt(sourceTemplateId) }) })
    const updatedSources = await fetchWithAuth('http://localhost:8000/api/sources').then(r => r.json())
    setEditingSource(updatedSources.find(s => s.id === editingSource.id)); setSourceTemplateId(""); fetchData()
  }

  const handleDetachSourceTemplate = async (tplId) => {
    await fetchWithAuth(`http://localhost:8000/api/sources/${editingSource.id}/templates/${tplId}`, { method: 'DELETE' })
    const updatedSources = await fetchWithAuth('http://localhost:8000/api/sources').then(r => r.json())
    setEditingSource(updatedSources.find(s => s.id === editingSource.id)); fetchData()
  }

  const handleToggleAutoPublish = async (source, checked) => {
    await fetchWithAuth(`http://localhost:8000/api/sources/${source.id}/auto-publish`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ auto_publish: checked, auto_template_id: checked ? source.auto_template_id : null })
    })
    fetchData()
  }

  const handleSetAutoTemplate = async (source, templateId) => {
    await fetchWithAuth(`http://localhost:8000/api/sources/${source.id}/auto-publish`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ auto_publish: source.auto_publish, auto_template_id: templateId ? parseInt(templateId) : null })
    })
    fetchData()
  }

  const openEditTemplate = (tpl) => {
    setEditingTemplate(tpl);
    setEditTemplateData({
      name: tpl.name, text: tpl.text || "", attach_mode: tpl.mode, folder_id: tpl.folder_id || "",
      media_json: JSON.parse(JSON.stringify(tpl.media_json || [])), buttons_json: JSON.parse(JSON.stringify(tpl.buttons_json || []))
    });
  }

  const closeEditTemplate = () => { setEditingTemplate(null); setEditTemplateData(null); }

  const handleUpdateTemplate = async (e) => {
    e.preventDefault();
    const cleanButtons = editTemplateData.buttons_json.filter(b => b.text && b.url);
    const res = await fetchWithAuth(`http://localhost:8000/api/templates/${editingTemplate.id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...editTemplateData, buttons_json: cleanButtons, folder_id: editTemplateData.folder_id ? parseInt(editTemplateData.folder_id) : null })
    });
    if (!res.ok) return alert("Ошибка обновления шаблона");
    closeEditTemplate(); fetchData();
  }

  const handleUploadEditTemplateMedia = async (e) => {
    const file = e.target.files[0]; if (!file) return
    setEditTplUploading(true); const formData = new FormData(); formData.append('file', file)
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/upload', { method: 'POST', body: formData })
      if (res.ok) { const data = await res.json(); setEditTemplateData(prev => ({ ...prev, media_json: [...(prev.media_json || []), data] })) }
    } finally { setEditTplUploading(false); e.target.value = null }
  }

  const removeEditTemplateMedia = (index) => { setEditTemplateData(prev => ({ ...prev, media_json: prev.media_json.filter((_, i) => i !== index) })) }
  const addEditTemplateButton = () => { setEditTemplateData(prev => ({ ...prev, buttons_json: [...(prev.buttons_json || []), { text: "", url: "" }] })) }
  const updateEditTemplateButton = (idx, field, value) => { const nb = [...editTemplateData.buttons_json]; nb[idx][field] = value; setEditTemplateData({ ...editTemplateData, buttons_json: nb }) }
  const removeEditTemplateButton = (idx) => { setEditTemplateData(prev => ({ ...prev, buttons_json: prev.buttons_json.filter((_, i) => i !== idx) })) }

  const handleUploadTemplateMedia = async (e) => {
    const file = e.target.files[0]; if (!file) return
    setTplUploading(true); const formData = new FormData(); formData.append('file', file)
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/upload', { method: 'POST', body: formData })
      if (res.ok) { const data = await res.json(); setNewTemplate(prev => ({ ...prev, media_json: [...(prev.media_json || []), data] })) }
    } finally { setTplUploading(false); e.target.value = null }
  }

  const removeTemplateMedia = (index) => setNewTemplate(prev => ({ ...prev, media_json: prev.media_json.filter((_, i) => i !== index) }))
  const addTemplateButton = () => setNewTemplate(prev => ({ ...prev, buttons_json: [...(prev.buttons_json || []), { text: "", url: "" }] }))
  const updateTemplateButton = (idx, field, value) => { const nb = [...newTemplate.buttons_json]; nb[idx][field] = value; setNewTemplate({ ...newTemplate, buttons_json: nb }) }
  const removeTemplateButton = (idx) => setNewTemplate(prev => ({ ...prev, buttons_json: prev.buttons_json.filter((_, i) => i !== idx) }))

  const handleCreateTemplate = async (e) => {
    e.preventDefault()
    const cleanButtons = newTemplate.buttons_json.filter(b => b.text && b.url)
    await fetchWithAuth('http://localhost:8000/api/templates', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...newTemplate, buttons_json: cleanButtons, folder_id: newTemplate.folder_id ? parseInt(newTemplate.folder_id) : null }) })
    setNewTemplate({ name: "", text: "", attach_mode: "append", folder_id: activeFolder || "", media_json: [], buttons_json: [] }); fetchData()
  }

  const handleDeleteTemplate = async (id) => { if (window.confirm("Удалить шаблон?")) { await fetchWithAuth(`http://localhost:8000/api/templates/${id}`, { method: 'DELETE' }); fetchData() } }
  const handleCreateFolder = async (e) => { e.preventDefault(); if (!newFolderName) return; await fetchWithAuth('http://localhost:8000/api/template-folders', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newFolderName }) }); setNewFolderName(""); fetchData() }
  const handleDeleteFolder = async (id) => { if (window.confirm("Удалить папку?")) { await fetchWithAuth(`http://localhost:8000/api/template-folders/${id}`, { method: 'DELETE' }); if (activeFolder === id) setActiveFolder(null); fetchData() } }

  const handleAddSource = async (e) => {
    e.preventDefault(); if (!newSourceInput) return
    setAddingSource(true)
    try {
      const res = await fetchWithAuth('http://localhost:8000/api/sources', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ channel_input: newSourceInput }) })
      if (res.ok) { setNewSourceInput(""); fetchData() } else { alert(`Ошибка: ${(await res.json()).detail}`) }
    } finally { setAddingSource(false) }
  }

  const handleToggleSource = async (id) => { await fetchWithAuth(`http://localhost:8000/api/sources/${id}/toggle`, { method: 'PATCH' }); fetchData() }
  const handleDeleteSource = async (id) => { if (window.confirm("Удалить источник?")) { await fetchWithAuth(`http://localhost:8000/api/sources/${id}`, { method: 'DELETE' }); fetchData() } }

  const openEditor = (post) => { setEditingPost(post); setEditText(post.text || ""); setWordCount(""); setPostButtons(post.buttons_json || []); setAiPrompt("") }
  const closeEditor = () => { setEditingPost(null); setEditText(""); setPostButtons([]); setShowLibSelector(false); setAiPrompt("") }
  
  const getMediaUrl = (key) => `http://localhost:9000/media/${key}?v=${cacheBuster}`
  const getStatusColor = (status) => ({ new: 'bg-blue-100 text-blue-800', published: 'bg-green-100 text-green-800', scheduled: 'bg-yellow-100 text-yellow-800', deleted: 'bg-red-100 text-red-800' }[status] || 'bg-gray-100')

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
      </div>
    )
  }

  if (loading) return <div className="text-center mt-20 text-xl">Загрузка...</div>
  
  const filteredTemplates = activeFolder ? templates.filter(t => t.folder_id === activeFolder) : templates
  const filteredQueuePosts = queueSourceFilter === 'all' ? posts : posts.filter(p => p.source === queueSourceFilter)

  return (
    <div className="max-w-7xl mx-auto p-4">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex gap-4 items-center">
            <button onClick={() => setActiveTab('posts')} className={`text-xl font-bold ${activeTab === 'posts' ? 'text-blue-600' : 'text-gray-400'}`}>Очередь</button>
            {activeTab === 'posts' && (
              <span className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded border border-green-200" title="Автообновление каждые 10 сек">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-ping"></span> Live
              </span>
            )}
            <button onClick={() => setActiveTab('trash')} className={`text-xl font-bold ${activeTab === 'trash' ? 'text-red-600' : 'text-gray-400'}`}>Корзина</button>
            <button onClick={() => setActiveTab('media')} className={`text-xl font-bold ${activeTab === 'media' ? 'text-blue-600' : 'text-gray-400'}`}>Медиа</button>
            <button onClick={() => setActiveTab('sources')} className={`text-xl font-bold ${activeTab === 'sources' ? 'text-blue-600' : 'text-gray-400'}`}>Источники</button>
            <button onClick={() => setActiveTab('templates')} className={`text-xl font-bold ${activeTab === 'templates' ? 'text-blue-600' : 'text-gray-400'}`}>Шаблоны</button>
            <button onClick={() => setActiveTab('metrics')} className={`text-xl font-bold ${activeTab === 'metrics' ? 'text-blue-600' : 'text-gray-400'}`}>Метрики</button>
          </div>
          
          <div className="flex gap-4 border-l pl-6 text-sm font-medium items-center">
            <div className="flex items-center gap-2 bg-gray-50 px-2 py-1 rounded border">
              <span className={`w-2.5 h-2.5 rounded-full ${status.bot_online ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              <span className={status.bot_online ? 'text-green-700' : 'text-red-700'}>Бот</span>
              {procStatus.bot ? (
                <button onClick={() => handleProcessAction('bot', 'stop')} className="text-xs text-red-500 hover:underline ml-2">Стоп</button>
              ) : (
                <button onClick={() => handleProcessAction('bot', 'start')} className="text-xs text-green-600 hover:underline ml-2">Запуск</button>
              )}
            </div>
            <div className="flex items-center gap-2 bg-gray-50 px-2 py-1 rounded border">
              <span className={`w-2.5 h-2.5 rounded-full ${status.collector_online ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              <span className={status.collector_online ? 'text-green-700' : 'text-red-700'}>Сборщик</span>
              {procStatus.collector ? (
                <button onClick={() => handleProcessAction('collector', 'stop')} className="text-xs text-red-500 hover:underline ml-2">Стоп</button>
              ) : (
                <button onClick={() => handleProcessAction('collector', 'start')} className="text-xs text-green-600 hover:underline ml-2">Запуск</button>
              )}
            </div>
            <button onClick={handleForceKillAll} className="text-xs bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700 font-bold" title="Убить все процессы bot.main и collector.main">
              🔧 Fix
            </button>
          </div>
        </div>
        <button onClick={() => { localStorage.removeItem('token'); setToken(null); }} className="text-sm text-red-500 hover:underline">Выйти</button>
      </div>
      
      {activeTab === 'posts' && (
        <div className="flex gap-6">
          <div className="w-1/4 bg-white p-4 rounded shadow h-fit flex flex-col gap-4">
            <button onClick={handleCreateManualPost} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded font-bold shadow transition">
              ➕ Создать пост
            </button>
            <div>
              <h2 className="text-lg font-bold mb-4">Папки</h2>
              <ul className="space-y-1">
                <li>
                  <button onClick={() => setQueueSourceFilter('all')} className={`w-full flex justify-between items-center text-left px-3 py-2 rounded ${queueSourceFilter === 'all' ? 'bg-blue-100 font-bold text-blue-800' : 'hover:bg-gray-100'}`}>
                    <span>📁 Все посты</span>
                    <span className="text-xs bg-gray-200 px-2 py-0.5 rounded-full text-gray-600">{posts.length}</span>
                  </button>
                </li>
                {sources.map(s => {
                  const count = posts.filter(p => p.source === s.username).length;
                  return (
                    <li key={s.id}>
                      <button onClick={() => setQueueSourceFilter(s.username)} className={`w-full flex justify-between items-center text-left px-3 py-2 rounded ${queueSourceFilter === s.username ? 'bg-blue-100 font-bold text-blue-800' : 'hover:bg-gray-100'}`}>
                        <span className="truncate pr-2">{s.username === 'manual' ? '✍️ Ручные' : `@${s.username}`}</span>
                        <span className="text-xs bg-gray-200 px-2 py-0.5 rounded-full text-gray-600">{count}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          </div>

          <div className="w-3/4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6">
              {filteredQueuePosts.map(post => (
                <div key={post.id} className="bg-white rounded-lg shadow-md overflow-hidden flex flex-col">
                  {post.media_count > 0 ? (
                    <div className="h-48 bg-gray-200 relative">
                      {post.media[0].type === 'video' ? (
                        <video src={getMediaUrl(post.media[0].key)} className="w-full h-full object-cover" controls />
                      ) : (
                        <img src={getMediaUrl(post.media[0].key)} className="w-full h-full object-cover" />
                      )}
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
                      {post.status === 'published' && (
                        <button onClick={() => handleAction(post.id, 'unpublish')} className="w-full bg-orange-500 hover:bg-orange-600 text-white py-2 rounded text-sm font-medium">↩️ Отменить публикацию</button>
                      )}
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
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold">Медиа-библиотека</h2>
            <div className="relative">
              <input type="file" onChange={handleUploadToLib} disabled={libUploading} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
              <button className="bg-blue-600 text-white px-4 py-2 rounded shadow text-sm font-bold">{libUploading ? 'Загрузка...' : '+ Загрузить файл'}</button>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {mediaLib.map(m => (
              <div key={m.id} className="bg-white rounded shadow overflow-hidden group relative h-32">
                {m.type === 'video' ? (
                  <video src={getMediaUrl(m.key)} className="w-full h-full object-cover" controls />
                ) : (
                  <img src={getMediaUrl(m.key)} className="w-full h-full object-cover" />
                )}
                <div className="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition z-10">
                  <button onClick={() => handleDownload(m.key, m.type)} title="Скачать" className="bg-blue-500 text-white w-6 h-6 flex items-center justify-center rounded">📥</button>
                  <button onClick={() => handleDeleteFromLib(m.id)} title="Удалить" className="bg-red-500 text-white w-6 h-6 flex items-center justify-center rounded">✕</button>
                </div>
              </div>
            ))}
            {mediaLib.length === 0 && <div className="col-span-full text-center py-10 text-gray-500">Библиотека пуста</div>}
          </div>
        </div>
      )}

      {activeTab === 'trash' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-700">Удаленные посты</h2>
            {trashPosts.length > 0 && <button onClick={handleEmptyTrash} className="bg-red-600 text-white px-4 py-2 rounded shadow text-sm font-bold">🗑 Очистить корзину</button>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trashPosts.map(post => (
              <div key={post.id} className="bg-gray-50 rounded-lg shadow-sm border border-gray-200 overflow-hidden flex flex-col opacity-80">
                {post.media_count > 0 ? (
                  <div className="h-48 bg-gray-200 relative grayscale">
                    {post.media[0].type === 'video' ? (
                      <video src={getMediaUrl(post.media[0].key)} className="w-full h-full object-cover" controls />
                    ) : (
                      <img src={getMediaUrl(post.media[0].key)} className="w-full h-full object-cover" />
                    )}
                  </div>
                ) : <div className="h-24 bg-gray-100 flex items-center justify-center text-gray-400">Без медиа</div>}
                <div className="p-4 flex-grow flex flex-col">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-500">@{post.source}</span>
                    <span className={`text-xs px-2 py-1 rounded-full font-bold uppercase bg-red-100 text-red-800`}>DELETED</span>
                  </div>
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
          <div className="bg-white p-6 rounded-lg shadow mb-8">
            <h2 className="text-xl font-bold mb-4">Добавить канал</h2>
            <div className="bg-blue-50 text-blue-800 p-4 rounded-lg mb-4 text-sm">
              <p className="font-bold mb-1">💡 Как добавить приватный канал?</p>
              <p>Перешли любое сообщение из этого канала в чат с ботом <b>@tel_forw_bot</b>.</p>
            </div>
            <form onSubmit={handleAddSource} className="flex gap-2">
              <input type="text" placeholder="@channel_name или -100..." className="flex-grow p-3 border rounded-lg outline-none" value={newSourceInput} onChange={e => setNewSourceInput(e.target.value)} disabled={addingSource} />
              <button type="submit" disabled={addingSource} className="bg-blue-600 text-white px-6 py-3 rounded-lg font-bold">Добавить</button>
            </form>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <h2 className="text-xl font-bold p-4 border-b">Активные источники</h2>
            <table className="w-full text-left">
              <thead><tr className="bg-gray-50 text-sm">
                <th className="p-4">Название</th>
                <th className="p-4 text-center">Статус</th>
                <th className="p-4 text-center">Авто-публикация</th>
                <th className="p-4 text-center">Шаблоны источника</th>
                <th className="p-4 text-right">Действия</th>
              </tr></thead>
              <tbody>
                {sources.map(src => (
                  <tr key={src.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="p-4">
                      <div className="font-bold">{src.title}</div>
                      <div className="text-sm text-gray-500">@{src.username}</div>
                    </td>
                    <td className="p-4 text-center">
                      <button onClick={() => handleToggleSource(src.id)} className={`px-3 py-1 rounded-full text-xs font-bold ${src.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-600'}`}>{src.enabled ? 'Активен' : 'Отключен'}</button>
                    </td>
                    <td className="p-4 text-center">
                      <div className="flex flex-col items-center gap-1">
                        <input 
                          type="checkbox" 
                          checked={src.auto_publish || false} 
                          onChange={(e) => handleToggleAutoPublish(src, e.target.checked)}
                          className="w-5 h-5 cursor-pointer accent-indigo-600" 
                          title="Включить авто-публикацию"
                        />
                        {src.auto_publish && (
                          <select 
                            value={src.auto_template_id || ""} 
                            onChange={(e) => handleSetAutoTemplate(src, e.target.value)}
                            className="text-xs p-1 border rounded w-full mt-1"
                          >
                            <option value="">-- Без шаблона --</option>
                            {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                          </select>
                        )}
                      </div>
                    </td>
                    <td className="p-4 text-center">
                      <button onClick={() => setEditingSource(src)} className="text-blue-600 text-sm font-medium">📎 {src.templates?.length || 0} шт.</button>
                    </td>
                    <td className="p-4 text-right">
                      <button onClick={() => handleDeleteSource(src.id)} className="text-red-500 text-sm font-medium">Удалить</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'templates' && (
        <div className="flex gap-6">
          <div className="w-1/4 bg-white p-4 rounded shadow h-fit">
            <h2 className="text-lg font-bold mb-4">Папки</h2>
            <ul className="mb-4 space-y-1">
              <li><button onClick={() => setActiveFolder(null)} className={`w-full text-left px-3 py-2 rounded ${activeFolder === null ? 'bg-blue-100 font-bold text-blue-800' : 'hover:bg-gray-100'}`}>Все шаблоны</button></li>
              {folders.map(f => (
                <li key={f.id} className="flex justify-between items-center group"><button onClick={() => setActiveFolder(f.id)} className={`flex-grow text-left px-3 py-2 rounded ${activeFolder === f.id ? 'bg-blue-100 font-bold text-blue-800' : 'hover:bg-gray-100'}`}>📁 {f.name}</button><button onClick={() => handleDeleteFolder(f.id)} className="text-red-400 opacity-0 group-hover:opacity-100 px-2">✕</button></li>
              ))}
            </ul>
            <form onSubmit={handleCreateFolder} className="flex gap-1"><input placeholder="Новая папка" className="border p-1 text-sm rounded w-full" value={newFolderName} onChange={e => setNewFolderName(e.target.value)} /><button type="submit" className="bg-gray-200 px-3 rounded text-sm font-bold">+</button></form>
          </div>
          <div className="w-3/4 flex gap-6">
            <div className="w-1/2">
              <h2 className="text-lg font-bold mb-4">Создать шаблон</h2>
              <form onSubmit={handleCreateTemplate} className="bg-white p-4 rounded shadow flex flex-col gap-3">
                <input placeholder="Название" className="p-2 border rounded" value={newTemplate.name} onChange={e => setNewTemplate({...newTemplate, name: e.target.value})} required />
                <textarea placeholder="Текст" className="p-2 border rounded h-24" value={newTemplate.text} onChange={e => setNewTemplate({...newTemplate, text: e.target.value})} />
                <select className="p-2 border rounded" value={newTemplate.attach_mode} onChange={e => setNewTemplate({...newTemplate, attach_mode: e.target.value})}><option value="append">В конец</option><option value="prepend">В начало</option><option value="standalone">Отдельное</option></select>
                <select className="p-2 border rounded" value={newTemplate.folder_id} onChange={e => setNewTemplate({...newTemplate, folder_id: e.target.value})}><option value="">-- Без папки --</option>{folders.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
                <div className="border-t pt-3 mt-1">
                  <label className="block text-xs font-bold text-gray-600 mb-1">Медиа шаблона</label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {newTemplate.media_json?.map((m, i) => (
                      <div key={i} className="relative w-12 h-12 border rounded group bg-gray-100">
                        {m.type === 'video' ? (
                           <video src={getMediaUrl(m.key)} className="w-full h-full object-cover" />
                        ) : (
                           <img src={getMediaUrl(m.key)} className="w-full h-full object-cover" />
                        )}
                        <button type="button" onClick={() => removeTemplateMedia(i)} className="absolute top-0 right-0 bg-red-500 text-white w-4 h-4 text-[10px] rounded-bl z-10">✕</button>
                      </div>
                    ))}
                  </div>
                  <input type="file" onChange={handleUploadTemplateMedia} disabled={tplUploading} className="block w-full text-xs" />
                </div>
                <div className="border-t pt-3 mt-1">
                  <label className="block text-xs font-bold text-gray-600 mb-1">🔗 Кнопки шаблона</label>
                  {newTemplate.buttons_json?.map((btn, idx) => (
                    <div key={idx} className="flex gap-1 mb-2">
                      <input placeholder="Текст" className="p-1 border rounded text-xs w-1/3" value={btn.text} onChange={e => updateTemplateButton(idx, 'text', e.target.value)} />
                      <input placeholder="https://..." className="p-1 border rounded text-xs flex-grow" value={btn.url} onChange={e => updateTemplateButton(idx, 'url', e.target.value)} />
                      <button type="button" onClick={() => removeTemplateButton(idx)} className="text-red-500 font-bold text-xs px-1">✕</button>
                    </div>
                  ))}
                  <button type="button" onClick={addTemplateButton} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">+ Кнопка</button>
                </div>
                <button type="submit" className="bg-blue-600 text-white py-2 rounded font-bold mt-2">Создать</button>
              </form>
            </div>
            <div className="w-1/2">
              <h2 className="text-lg font-bold mb-4">{activeFolder ? folders.find(f => f.id === activeFolder)?.name : "Все шаблоны"}</h2>
              <div className="flex flex-col gap-3 max-h-[60vh] overflow-y-auto pr-2">
                {filteredTemplates.map(t => (
                  <div key={t.id} className="bg-white p-3 rounded shadow flex flex-col justify-between">
                    <div className="flex justify-between items-start">
                      <div><h3 className="font-bold">{t.name} <span className="text-xs font-normal text-gray-500">({t.mode})</span></h3><p className="text-sm text-gray-600 mt-1 whitespace-pre-wrap">{t.text}</p></div>
                      <div className="flex gap-2">
                        <button onClick={() => openEditTemplate(t)} className="text-blue-500 text-sm font-medium">✏️</button>
                        <button onClick={() => handleDeleteTemplate(t.id)} className="text-red-500 text-sm font-medium">Удалить</button>
                      </div>
                    </div>
                    {t.media_json?.length > 0 && (
                      <div className="flex gap-1 mt-2">
                        {t.media_json.map((m, i) => (
                          m.type === 'video' ? <video key={i} src={getMediaUrl(m.key)} className="w-8 h-8 object-cover rounded" /> : <img key={i} src={getMediaUrl(m.key)} className="w-8 h-8 object-cover rounded" />
                        ))}
                      </div>
                    )}
                    {t.buttons_json?.length > 0 && <div className="text-xs text-blue-500 mt-2">🔗 {t.buttons_json.length} кнопок(и)</div>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'metrics' && metrics && (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white p-6 rounded-lg shadow border-t-4 border-blue-500"><p className="text-gray-500 text-sm font-bold uppercase">Всего</p><p className="text-4xl font-bold text-gray-800 mt-2">{metrics.summary.total}</p></div>
            <div className="bg-white p-6 rounded-lg shadow border-t-4 border-green-500"><p className="text-gray-500 text-sm font-bold uppercase">Опубликовано</p><p className="text-4xl font-bold text-green-600 mt-2">{metrics.summary.published}</p></div>
            <div className="bg-white p-6 rounded-lg shadow border-t-4 border-red-500"><p className="text-gray-500 text-sm font-bold uppercase">Удалено</p><p className="text-4xl font-bold text-red-600 mt-2">{metrics.summary.deleted}</p></div>
            <div className="bg-white p-6 rounded-lg shadow border-t-4 border-yellow-500"><p className="text-gray-500 text-sm font-bold uppercase">В очереди</p><p className="text-4xl font-bold text-yellow-600 mt-2">{metrics.summary.pending}</p></div>
          </div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">Эффективность источников</h2>
            <button onClick={handleClearChannel} disabled={clearing} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded shadow text-sm font-bold disabled:opacity-50">
              {clearing ? 'Очистка...' : '🧹 Очистить канал'}
            </button>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead><tr className="bg-gray-100 text-gray-600 text-sm uppercase"><th className="p-4 border-b">Канал</th><th className="p-4 border-b text-center">Всего</th><th className="p-4 border-b text-center text-green-600">Опубл.</th><th className="p-4 border-b text-center text-red-600">Удалено</th><th className="p-4 border-b text-center">КПД</th></tr></thead>
              <tbody>{metrics.sources.map((src, idx) => (<tr key={idx} className="hover:bg-gray-50 border-b last:border-0"><td className="p-4 font-medium">{src.source === '@manual' ? '✍️ Ручные' : src.source}</td><td className="p-4 text-center">{src.total}</td><td className="p-4 text-center font-bold text-green-600">{src.published}</td><td className="p-4 text-center font-bold text-red-600">{src.deleted}</td><td className="p-4 text-center"><div className="flex items-center justify-center gap-2"><span className="font-bold text-lg w-12">{src.efficiency}%</span><div className="w-32 bg-gray-200 rounded-full h-2.5"><div className={`h-2.5 rounded-full ${src.efficiency > 70 ? 'bg-green-500' : src.efficiency > 40 ? 'bg-yellow-400' : 'bg-red-500'}`} style={{ width: `${src.efficiency}%` }}></div></div></div></td></tr>))}</tbody>
            </table>
          </div>
        </div>
      )}

      {editingPost && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col overflow-hidden max-h-[90vh]">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h2 className="text-lg font-bold">Пост #{editingPost.id}</h2>
              <button onClick={closeEditor} className="text-2xl leading-none">&times;</button>
            </div>
            <div className="p-4 overflow-y-auto">
              <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm font-medium">Медиа ({editingPost.media?.length || 0})</label>
                  <div className="flex gap-2">
                    <button onClick={() => handleRefetch(editingPost.id)} disabled={refetching} className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded font-bold hover:bg-gray-300 disabled:opacity-50">
                      {refetching ? 'Скачивание...' : '🔄 Скачать заново'}
                    </button>
                    <button onClick={() => setShowLibSelector(true)} className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded font-bold hover:bg-purple-200">📁 Из библиотеки</button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {editingPost.media?.map(m => (
                    <div key={m.id} className="relative w-20 h-20 border rounded group bg-gray-100">
                      {m.type === 'video' ? (
                        <video src={getMediaUrl(m.key)} className="w-full h-full object-cover" controls />
                      ) : (
                        <img src={getMediaUrl(m.key)} className="w-full h-full object-cover" />
                      )}
                      <div className="absolute top-0 right-0 flex opacity-0 group-hover:opacity-100 transition z-10">
                        <button onClick={() => handleDownload(m.key, m.type)} title="Скачать на ПК" className="bg-green-500 text-white w-6 h-6 flex items-center justify-center text-xs">📥</button>
                        <button onClick={() => handleSaveToLib(m.id)} title="Сохранить в библиотеку" className="bg-blue-500 text-white w-6 h-6 flex items-center justify-center text-xs">💾</button>
                        <button onClick={() => handleDeleteMedia(m.id)} title="Удалить" className="bg-red-500 text-white w-6 h-6 flex items-center justify-center text-xs">✕</button>
                      </div>
                    </div>
                  ))}
                </div>
                <input type="file" onChange={handleUploadMedia} disabled={uploading} className="mt-2 block w-full text-sm" />
              </div>

              <div className="mb-4 bg-purple-50 p-3 rounded border border-purple-100">
                <label className="block text-sm font-bold text-purple-800 mb-2">📎 Шаблоны поста</label>
                <div className="flex flex-col gap-2 mb-3">{editingPost.templates?.map(t => (<div key={t.id} className="flex justify-between items-center bg-white p-2 rounded shadow-sm text-sm"><span>{t.name} ({t.mode})</span><button onClick={() => handleDetachTemplate(t.id)} className="text-red-500 font-bold">✕</button></div>))}</div>
                <div className="flex gap-2">
                  <select className="border rounded p-1 text-sm flex-grow" value={selectedTemplate} onChange={e => setSelectedTemplate(e.target.value)}>
                    <option value="">-- Выбрать шаблон --</option>
                    {folders.map(folder => { const ft = templates.filter(t => t.folder_id === folder.id); if (!ft.length) return null; return <optgroup key={folder.id} label={folder.name}>{ft.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</optgroup> })}
                    <optgroup label="Без папки">{templates.filter(t => !t.folder_id).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</optgroup>
                  </select>
                  <select className="border rounded p-1 text-sm" value={attachMode} onChange={e => setAttachMode(e.target.value)}><option value="append">В конец</option><option value="prepend">В начало</option></select>
                  <button onClick={handleAttachTemplate} className="bg-purple-600 text-white px-3 py-1 rounded text-sm">Добавить</button>
                </div>
              </div>

              <div className="mb-4 bg-gray-100 p-3 rounded border border-gray-200">
                <label className="block text-sm font-bold text-gray-700 mb-2">🤖 Помощник ИИ</label>
                
                <div className="flex gap-2 mb-2">
                  <input 
                    placeholder="Задание для ИИ (например: 'Напиши пост про ...')" 
                    className="flex-grow p-2 border rounded text-sm"
                    value={aiPrompt}
                    onChange={e => setAiPrompt(e.target.value)}
                  />
                  <button onClick={handleGenerateText} disabled={aiGenerating} className="bg-pink-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50 whitespace-nowrap">
                    {aiGenerating ? '...' : '✨ Написать с ИИ'}
                  </button>
                </div>

                <div className="flex flex-wrap gap-2 items-center">
                  <button onClick={handleTranslate} disabled={aiLoading} className="bg-indigo-500 text-white px-3 py-1.5 rounded text-sm disabled:opacity-50">🇷🇺 Перевести</button>
                  <div className="flex items-center gap-1 bg-white border rounded px-2 py-1">
                    <input type="number" placeholder="Слов" className="w-16 outline-none text-sm" value={wordCount} onChange={e => setWordCount(e.target.value)} />
                    <button onClick={handleRewrite} disabled={aiLoading} className="bg-indigo-500 text-white px-3 py-1.5 rounded text-sm disabled:opacity-50">🔄 Рерайт</button>
                  </div>
                  <button onClick={handleClearLinks} disabled={linkClearing} className="bg-gray-600 text-white px-3 py-1.5 rounded text-sm disabled:opacity-50">
                    {linkClearing ? '...' : '🧹 Очистить ссылки'}
                  </button>
                  {aiLoading && <span className="text-sm text-indigo-600 animate-pulse ml-auto">Нейросеть думает...</span>}
                </div>
              </div>

              <div className="mb-4 bg-blue-50 p-3 rounded border border-blue-100">
                <label className="block text-sm font-bold text-blue-800 mb-2">🔗 Кнопки под постом</label>
                {postButtons.map((btn, idx) => (
                  <div key={idx} className="flex gap-2 mb-2">
                    <input placeholder="Текст кнопки" className="p-1 border rounded text-sm w-1/3" value={btn.text} onChange={e => { const nb = [...postButtons]; nb[idx].text = e.target.value; setPostButtons(nb); }} />
                    <input placeholder="https://ссылка" className="p-1 border rounded text-sm flex-grow" value={btn.url} onChange={e => { const nb = [...postButtons]; nb[idx].url = e.target.value; setPostButtons(nb); }} />
                    <button onClick={() => setPostButtons(postButtons.filter((_, i) => i !== idx))} className="text-red-500 font-bold px-2">✕</button>
                  </div>
                ))}
                <button onClick={() => setPostButtons([...postButtons, { text: "", url: "" }])} className="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded hover:bg-blue-200 mt-1 font-medium">+ Добавить кнопку</button>
              </div>

              <label className="block text-sm font-medium mb-1">Текст поста</label>
              <textarea className="w-full h-32 p-2 border rounded-lg text-sm" value={editText} onChange={(e) => setEditText(e.target.value)} />
            </div>
            <div className="p-4 border-t bg-gray-50 flex justify-end gap-3">
              <button onClick={closeEditor} className="px-4 py-2 text-gray-600">Отмена</button>
              <button onClick={saveEdit} className="px-4 py-2 bg-blue-600 text-white rounded">Сохранить</button>
            </div>
          </div>
        </div>
      )}

      {showLibSelector && editingPost && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-3xl flex flex-col overflow-hidden max-h-[80vh]">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h2 className="text-lg font-bold">Выбрать из библиотеки</h2>
              <button onClick={() => setShowLibSelector(false)} className="text-2xl leading-none">&times;</button>
            </div>
            <div className="p-4 overflow-y-auto">
              <div className="grid grid-cols-3 md:grid-cols-5 gap-4">
                {mediaLib.map(m => (
                  <div key={m.id} onClick={() => handleAttachFromLib(m.id)} className="cursor-pointer border rounded overflow-hidden hover:ring-2 hover:ring-blue-500 transition group relative h-24 bg-gray-100">
                    {m.type === 'video' ? (
                      <video src={getMediaUrl(m.key)} className="w-full h-full object-cover" controls />
                    ) : (
                      <img src={getMediaUrl(m.key)} className="w-full h-full object-cover" />
                    )}
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 flex items-center justify-center transition z-0">
                      <span className="text-white opacity-0 group-hover:opacity-100 font-bold">+ Добавить</span>
                    </div>
                  </div>
                ))}
                {mediaLib.length === 0 && <div className="col-span-full text-center py-8 text-gray-500">Библиотека пуста</div>}
              </div>
            </div>
          </div>
        </div>
      )}

      {editingSource && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg flex flex-col overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50"><h2 className="text-lg font-bold">Шаблоны для {editingSource.title}</h2><button onClick={() => setEditingSource(null)} className="text-2xl leading-none">&times;</button></div>
            <div className="p-4 overflow-y-auto">
              <p className="text-sm text-gray-500 mb-4">Эти шаблоны будут отправляться <b>отдельными сообщениями</b> после публикации.</p>
              <div className="flex flex-col gap-2 mb-4">{editingSource.templates?.map(t => (<div key={t.id} className="flex justify-between items-center bg-gray-50 p-2 rounded shadow-sm text-sm"><span>📎 {t.name}</span><button onClick={() => handleDetachSourceTemplate(t.id)} className="text-red-500 font-bold">✕</button></div>))}</div>
              <div className="flex gap-2 border-t pt-4">
                <select className="border rounded p-2 text-sm flex-grow" value={sourceTemplateId} onChange={e => setSourceTemplateId(e.target.value)}><option value="">-- Выбрать шаблон --</option>{templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
                <button onClick={handleAttachSourceTemplate} className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-bold">Прикрепить</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {editingTemplate && editTemplateData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col overflow-hidden max-h-[90vh]">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h2 className="text-lg font-bold">Редактирование шаблона: {editingTemplate.name}</h2>
              <button onClick={closeEditTemplate} className="text-2xl leading-none">&times;</button>
            </div>
            <div className="p-4 overflow-y-auto">
              <form id="editTemplateForm" onSubmit={handleUpdateTemplate} className="flex flex-col gap-3">
                <input placeholder="Название" className="p-2 border rounded" value={editTemplateData.name} onChange={e => setEditTemplateData({...editTemplateData, name: e.target.value})} required />
                <textarea placeholder="Текст" className="p-2 border rounded h-24" value={editTemplateData.text} onChange={e => setEditTemplateData({...editTemplateData, text: e.target.value})} />
                <select className="p-2 border rounded" value={editTemplateData.attach_mode} onChange={e => setEditTemplateData({...editTemplateData, attach_mode: e.target.value})}>
                  <option value="append">В конец</option><option value="prepend">В начало</option><option value="standalone">Отдельное</option>
                </select>
                <select className="p-2 border rounded" value={editTemplateData.folder_id} onChange={e => setEditTemplateData({...editTemplateData, folder_id: e.target.value})}>
                  <option value="">-- Без папки --</option>{folders.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                </select>

                <div className="border-t pt-3 mt-1">
                  <label className="block text-xs font-bold text-gray-600 mb-1">Медиа шаблона</label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {editTemplateData.media_json?.map((m, i) => (
                      <div key={i} className="relative w-12 h-12 border rounded group bg-gray-100">
                        {m.type === 'video' ? (
                           <video src={getMediaUrl(m.key)} className="w-full h-full object-cover" />
                        ) : (
                           <img src={getMediaUrl(m.key)} className="w-full h-full object-cover" />
                        )}
                        <button type="button" onClick={() => removeEditTemplateMedia(i)} className="absolute top-0 right-0 bg-red-500 text-white w-4 h-4 text-[10px] rounded-bl z-10">✕</button>
                      </div>
                    ))}
                  </div>
                  <input type="file" onChange={handleUploadEditTemplateMedia} disabled={editTplUploading} className="block w-full text-xs" />
                </div>

                <div className="border-t pt-3 mt-1">
                  <label className="block text-xs font-bold text-gray-600 mb-1">🔗 Кнопки шаблона</label>
                  {editTemplateData.buttons_json?.map((btn, idx) => (
                    <div key={idx} className="flex gap-1 mb-2">
                      <input placeholder="Текст" className="p-1 border rounded text-xs w-1/3" value={btn.text} onChange={e => updateEditTemplateButton(idx, 'text', e.target.value)} />
                      <input placeholder="https://..." className="p-1 border rounded text-xs flex-grow" value={btn.url} onChange={e => updateEditTemplateButton(idx, 'url', e.target.value)} />
                      <button type="button" onClick={() => removeEditTemplateButton(idx)} className="text-red-500 font-bold text-xs px-1">✕</button>
                    </div>
                  ))}
                  <button type="button" onClick={addEditTemplateButton} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">+ Кнопка</button>
                </div>
              </form>
            </div>
            <div className="p-4 border-t bg-gray-50 flex justify-end gap-3">
              <button onClick={closeEditTemplate} className="px-4 py-2 text-gray-600">Отмена</button>
              <button type="submit" form="editTemplateForm" className="px-4 py-2 bg-blue-600 text-white rounded font-bold">Сохранить изменения</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App