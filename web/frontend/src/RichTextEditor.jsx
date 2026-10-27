import { useEffect, useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Node } from '@tiptap/core'

// Кастомное расширение для спойлера Telegram (<tg-spoiler>)
const Spoiler = Node.create({
  name: 'spoiler',
  group: 'inline',
  inline: true,
  addAttributes() {
    return {}
  },
  parseHTML() {
    return [{ tag: 'tg-spoiler' }]
  },
  renderHTML() {
    return ['tg-spoiler', 0]
  },
})

const RichTextEditor = ({ value, onChange }) => {
  // Собственный диалог для ввода ссылки (без нативного window.prompt)
  const [linkDialogOpen, setLinkDialogOpen] = useState(false)
  const [linkUrl, setLinkUrl] = useState('')

  const editor = useEditor({
    extensions: [
      // В tiptap 3 Link уже входит в StarterKit — настраиваем его здесь,
      // отдельное расширение добавлять нельзя (будет дубликат "link").
      StarterKit.configure({
        heading: false,
        link: {
          openOnClick: false,
          autolink: true,
        },
      }),
      Spoiler,
    ],
    content: value || '',
    onUpdate: ({ editor }) => {
      // При каждом изменении передаем HTML наверх в App.jsx
      onChange(editor.getHTML())
    },
    editorProps: {
      attributes: {
        // Стилизуем сам контейнер редактора
        class: 'prose prose-sm focus:outline-none min-h-[150px] p-2 border rounded-b-lg',
      },
    },
  })

  // Синхронизация внешнего значения (например, после работы ИИ или цепочки)
  useEffect(() => {
    if (!editor || value === undefined || value === null) return
    const current = editor.getHTML()
    if (value === current) return
    // Пустой редактор отдаёт <p></p>, не зацикливаемся на этом
    if (value === '' && current === '<p></p>') return
    editor.commands.setContent(value, false)
  }, [value, editor])

  if (!editor) {
    return null
  }

  // Открыть диалог добавления ссылки
  const setLink = () => {
    setLinkUrl(editor.getAttributes('link').href || '')
    setLinkDialogOpen(true)
  }

  const applyLink = () => {
    const url = linkUrl.trim()
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
    } else {
      editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
    }
    setLinkDialogOpen(false)
  }

  return (
    <div className="border rounded-lg overflow-hidden bg-white">
      {/* Панель инструментов */}
      <div className="flex flex-wrap gap-1 p-2 bg-gray-50 border-b [&>button]:min-h-[36px]">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          disabled={!editor.can().chain().focus().toggleBold().run()}
          className={`px-3 py-1 rounded text-sm font-bold ${editor.isActive('bold') ? 'bg-blue-600 text-white' : 'hover:bg-gray-200'}`}
        >
          B
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          disabled={!editor.can().chain().focus().toggleItalic().run()}
          className={`px-3 py-1 rounded text-sm italic ${editor.isActive('italic') ? 'bg-blue-600 text-white' : 'hover:bg-gray-200'}`}
        >
          I
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleStrike().run()}
          disabled={!editor.can().chain().focus().toggleStrike().run()}
          className={`px-3 py-1 rounded text-sm line-through ${editor.isActive('strike') ? 'bg-blue-600 text-white' : 'hover:bg-gray-200'}`}
        >
          S
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleCode().run()}
          disabled={!editor.can().chain().focus().toggleCode().run()}
          className={`px-3 py-1 rounded text-sm font-mono ${editor.isActive('code') ? 'bg-blue-600 text-white' : 'hover:bg-gray-200'}`}
        >
          {'</>'}
        </button>
        <button
          type="button"
          onClick={setLink}
          className={`px-3 py-1 rounded text-sm ${editor.isActive('link') ? 'bg-blue-600 text-white' : 'hover:bg-gray-200'}`}
        >
          🔗 Ссылка
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleNode('spoiler', 'text').run()}
          className={`px-3 py-1 rounded text-sm ${editor.isActive('spoiler') ? 'bg-blue-600 text-white' : 'hover:bg-gray-200'}`}
        >
          🙈 Спойлер
        </button>
      </div>

      {/* Само поле ввода */}
      <EditorContent editor={editor} />

      {/* Диалог ввода ссылки */}
      {linkDialogOpen && (
        <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b">
              <h3 className="font-bold text-gray-800">Ссылка</h3>
              <button type="button" onClick={() => setLinkDialogOpen(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <div className="p-5">
              <input
                type="url"
                autoFocus
                placeholder="https://..."
                value={linkUrl}
                onChange={e => setLinkUrl(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); applyLink() } }}
                className="w-full p-3 border rounded-lg outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
              <p className="text-xs text-gray-400 mt-2">Оставьте поле пустым, чтобы убрать ссылку.</p>
            </div>
            <div className="flex justify-end gap-2 px-5 py-4 bg-gray-50 border-t">
              <button type="button" onClick={() => setLinkDialogOpen(false)} className="px-4 py-2 text-gray-600 font-medium hover:bg-gray-100 rounded-lg transition">Отмена</button>
              <button type="button" onClick={applyLink} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold transition">ОК</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default RichTextEditor
