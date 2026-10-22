import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
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
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false, // Отключаем заголовки, если не нужны
      }),
      Link.configure({
        openOnClick: false,
        autolink: true,
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

  if (!editor) {
    return null
  }

  // Вспомогательная функция для добавления ссылки
  const setLink = () => {
    const previousUrl = editor.getAttributes('link').href
    const url = window.prompt('URL', previousUrl)

    if (url === null) return // Отмена
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
  }

  return (
    <div className="border rounded-lg overflow-hidden bg-white">
      {/* Панель инструментов */}
      <div className="flex flex-wrap gap-1 p-2 bg-gray-50 border-b">
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
    </div>
  )
}

export default RichTextEditor