import DOMPurify from 'dompurify'

const ALLOWED_TAGS = [
  'p', 'strong', 'b', 'em', 'i', 'code', 'pre', 'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'a', 'blockquote',
  'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div',
  'hr', 'sup', 'sub', 'del', 'ins', 'mark',
]

const ALLOWED_ATTR = ['class', 'href', 'target', 'rel']

export function sanitizeHtml(dirty) {
  if (!dirty) return ''
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
  })
}
