/**
 * 手机拟真与社交交互内容解析器 (Phone & Social Interaction Parser)
 * 解析 Pass 2 输出中的朋友圈、论坛 BBS、手机即时消息、语音、定位与转账
 * 兼容未闭合流式文本与标准酒馆正则语法
 */

export interface MomentsComment {
  author: string
  text: string
}

export interface MomentsPost {
  id: string
  author: string
  text: string
  imageDesc?: string
  likes: string[]
  comments: MomentsComment[]
}

export interface ForumComment {
  author: string
  replyTo?: string
  text: string
}

export interface ForumData {
  boardName: string
  author: string
  title: string
  body: string
  imageDesc?: string
  statsStr: string
  isLocked: boolean
  comments: ForumComment[]
}

export interface ChatMessageItem {
  id: string
  type: 'message' | 'voice' | 'location' | 'transfer'
  sender: string
  content: string
  extra?: {
    duration?: string
    locationTitle?: string
    locationDesc?: string
    amount?: string
    note?: string
  }
}

export type ParsedContentBlock =
  | { type: 'text'; content: string }
  | { type: 'moments'; posts: MomentsPost[] }
  | { type: 'forum'; data: ForumData }
  | { type: 'chat'; items: ChatMessageItem[] }

/**
 * 清理名字中的括号附言，提取主名与备用名 (例如: "苏晓 (调查员)" -> { name: "苏晓", alias: "调查员" })
 */
export function parseAuthorName(rawName: string): { name: string; alias?: string } {
  const trimmed = (rawName || '').trim()
  const match = trimmed.match(/^([^\\(（]+)\s*[\\(（]([^\\)）]+)[\\)）]/)
  if (match) {
    return { name: match[1].trim(), alias: match[2].trim() }
  }
  return { name: trimmed }
}

/**
 * 解析朋友圈块内容
 */
function parseMomentsContent(rawBlock: string): MomentsPost[] {
  const cleaned = rawBlock.replace(/^[<＜]朋友圈[>＞]/i, '').replace(/[<＜]\/朋友圈[>＞]$/i, '').trim()
  // 按 [发布... 分块
  const postBlocks = cleaned.split(/(?=\s*\[发布[|:：]-?)/).map((b) => b.trim()).filter(Boolean)
  const posts: MomentsPost[] = []

  const publishRegex = /^\[发布[|:：]([^\]]+)\][：:]([\s\S]*?)(?=\s*\[|$)/
  const likesRegex = /\[点赞\][：:](.*)/
  const commentsRegex = /\[评论[|:：]([^\]]+)\][：:](.*)/

  for (const block of postBlocks) {
    const lines = block.split('\n').map((l) => l.trim()).filter(Boolean)
    if (!lines.length) continue

    const pubMatch = lines[0].match(publishRegex)
    if (!pubMatch) {
      // 容错：若未严格以 [发布: 开头，尝试整个块提取
      const fallbackPub = block.match(/\[发布[|:：]([^\]]+)\][：:]([\s\S]*)/)
      if (!fallbackPub) continue
    }

    const author = pubMatch ? pubMatch[1].trim() : '匿名好友'
    let rawText = pubMatch ? pubMatch[2].trim() : ''

    // 提取图片描述 {{...}}
    let imageDesc: string | undefined
    const imgMatch = rawText.match(/{{\s*([^}]+)\s*}}/)
    if (imgMatch) {
      imageDesc = imgMatch[1].trim()
      rawText = rawText.replace(/{{\s*[^}]+\s*}}/, '').trim()
    }

    const likes: string[] = []
    const comments: MomentsComment[] = []

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i]
      const likeM = line.match(likesRegex)
      if (likeM) {
        const rawLikes = likeM[1].trim()
        if (rawLikes) {
          rawLikes.split(/[,，、]/).forEach((n) => {
            const trimmed = n.trim()
            if (trimmed) likes.push(trimmed)
          })
        }
        continue
      }

      const commentM = line.match(commentsRegex)
      if (commentM) {
        comments.push({
          author: commentM[1].trim(),
          text: commentM[2].trim(),
        })
      }
    }

    posts.push({
      id: `moment-${author}-${Math.random().toString(36).slice(2, 7)}`,
      author,
      text: rawText,
      imageDesc,
      likes,
      comments,
    })
  }

  return posts
}

/**
 * 解析网络论坛与社区热帖块内容
 */
function parseForumContent(rawBlock: string): ForumData {
  const cleaned = rawBlock.replace(/^[<＜]论坛[>＞]/i, '').replace(/[<＜]\/论坛[>＞]$/i, '').trim()
  const lines = cleaned.split('\n').map((l) => l.trim()).filter(Boolean)

  let boardName = '渡鸦低语'
  let author = '匿名渡鸦'
  let title = ''
  let body = ''
  let isLocked = false
  let statsStr = '1.2k 浏览 · 184 点赞'
  const comments: ForumComment[] = []

  for (const line of lines) {
    const boardM = line.match(/^\[(板块|分区)[-|：:]\s*(.+?)\]/)
    if (boardM) {
      boardName = boardM[2].trim()
      continue
    }

    const postM = line.match(/^\[(贴子|主贴|发帖)[-|:：]([^\]\|]+)(?:\|([^\]]+))?\]\s*[:：]\s*([\s\S]*)$/)
    if (postM) {
      author = postM[2].trim()
      title = (postM[3] || '').trim()
      body = (postM[4] || '').trim()
      continue
    }

    if (/^\[(状态|权限)[-|:：]\s*(禁止评论|锁定|只读|locked)\]/i.test(line)) {
      isLocked = true
      continue
    }

    const statsM = line.match(/^\[(热度|数据|浏览)[-|:：]\s*([\s\S]+?)\]/)
    if (statsM) {
      statsStr = statsM[2].trim()
      continue
    }

    const commentM = line.match(/^\[(评论|回帖)[-|:：]([^\]]+)\]\s*[:：]\s*([\s\S]+)$/)
    if (commentM) {
      const fullAuthor = commentM[2].trim()
      const text = commentM[3].trim()
      let authorName = fullAuthor
      let replyTo: string | undefined

      if (fullAuthor.includes('回复')) {
        const parts = fullAuthor.split('回复')
        authorName = parts[0].trim()
        replyTo = parts[1].trim()
      }

      comments.push({ author: authorName, replyTo, text })
    }
  }

  // 提取帖子正文内的图片描述
  let imageDesc: string | undefined
  const imgMatch = body.match(/{{\s*([^}]+)\s*}}/)
  if (imgMatch) {
    imageDesc = imgMatch[1].trim()
    body = body.replace(/{{\s*[^}]+\s*}}/, '').trim()
  }

  return {
    boardName,
    author,
    title,
    body,
    imageDesc,
    statsStr,
    isLocked,
    comments,
  }
}

/**
 * 单行尝试匹配手机消息/语音/定位/转账
 */
function tryParseChatLine(line: string): ChatMessageItem | null {
  const trimmed = line.trim()
  if (!trimmed) return null

  // 1. 语音消息: [语音-发信人|时长]: 内容
  const voiceM = trimmed.match(/^\[语音[-|:：]([^|]+)\|([^\]]+)\]\s*[:：]\s*([\s\S]+)$/)
  if (voiceM) {
    return {
      id: `chat-${Math.random().toString(36).slice(2, 7)}`,
      type: 'voice',
      sender: voiceM[1].trim(),
      content: voiceM[3].trim(),
      extra: { duration: voiceM[2].trim() },
    }
  }

  // 2. 定位消息: [定位-发信人]:[标题-具体地址] 或 [定位-发信人]:[具体地址]
  const locM = trimmed.match(/^\[定位[-|:：]([^\]]+)\]\s*[:：]\s*\[(?:(.*)-)?([^\]]+)\]$/)
  if (locM) {
    return {
      id: `chat-${Math.random().toString(36).slice(2, 7)}`,
      type: 'location',
      sender: locM[1].trim(),
      content: locM[3].trim(),
      extra: {
        locationDesc: locM[2] ? locM[2].trim() : undefined,
        locationTitle: locM[3].trim(),
      },
    }
  }

  // 3. 转账消息: [转账-发信人]: 金额 (附言备注)
  const transferM = trimmed.match(/^\[转账[-|:：]([^\]]+)\]\s*[:：]\s*([\s\S]+)$/)
  if (transferM) {
    const rawVal = transferM[2].trim()
    let amount = rawVal
    let note = ''
    // 支持全角/半角括号包裹的附言，如 "¥5000.00 (首期调查勘察经费)" 或 "5000元（预付款）"
    const bracketMatch = rawVal.match(/^([^\(（]+?)[\s]*[\(（]([^\)）]+)[\)）]$/)
    if (bracketMatch) {
      amount = bracketMatch[1].trim()
      note = bracketMatch[2].trim()
    } else {
      const spaceMatch = rawVal.match(/^([¥￥$€]?[0-9\.,]+(?:元|块)?)\s+([\s\S]+)$/)
      if (spaceMatch) {
        amount = spaceMatch[1].trim()
        note = spaceMatch[2].trim()
      }
    }

    return {
      id: `chat-${Math.random().toString(36).slice(2, 7)}`,
      type: 'transfer',
      sender: transferM[1].trim(),
      content: rawVal,
      extra: {
        amount,
        note: note || '转账附言',
      },
    }
  }

  // 4. 普通即时消息: [消息-发信人]: 内容
  const msgM = trimmed.match(/^\[消息[-|:：]([^\]]+)\]\s*[:：]\s*([\s\S]+)$/)
  if (msgM) {
    return {
      id: `chat-${Math.random().toString(36).slice(2, 7)}`,
      type: 'message',
      sender: msgM[1].trim(),
      content: msgM[2].trim(),
    }
  }

  return null
}

/**
 * 主入口：将推演正文文本拆分为结构化内容块流
 */
export function parseProseIntoBlocks(prose: string): ParsedContentBlock[] {
  if (!prose || !prose.trim()) return []

  const blocks: ParsedContentBlock[] = []

  // 步骤 1: 扫描朋友圈与论坛标签
  // 匹配 <朋友圈>...</朋友圈> 或未闭合的 <朋友圈>...（针对流式状态）
  // 匹配 <论坛>...</论坛> 或未闭合的 <论坛>...
  const tagRegex = /([<＜](?:朋友圈|论坛)[>＞][\s\S]*?(?:[<＜]\/(?:朋友圈|论坛)[>＞]|$))/gi
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = tagRegex.exec(prose)) !== null) {
    // 标签之前的部分
    const beforeText = prose.slice(lastIndex, match.index)
    if (beforeText.trim()) {
      parseTextAndChatSegments(beforeText, blocks)
    }

    const tagContent = match[0]
    if (/^[<＜]朋友圈[>＞]/i.test(tagContent)) {
      const posts = parseMomentsContent(tagContent)
      if (posts.length > 0) {
        blocks.push({ type: 'moments', posts })
      } else {
        blocks.push({ type: 'text', content: tagContent })
      }
    } else if (/^[<＜]论坛[>＞]/i.test(tagContent)) {
      const forumData = parseForumContent(tagContent)
      blocks.push({ type: 'forum', data: forumData })
    }

    lastIndex = tagRegex.lastIndex
  }

  // 标签剩余末尾部分
  const remaining = prose.slice(lastIndex)
  if (remaining.trim()) {
    parseTextAndChatSegments(remaining, blocks)
  }

  return blocks
}

/**
 * 辅助：将普通文本段落与聊天消息行分别提取并连缀
 */
function parseTextAndChatSegments(text: string, outputBlocks: ParsedContentBlock[]) {
  const lines = text.split('\n')
  let currentChatItems: ChatMessageItem[] = []
  let currentParagraphLines: string[] = []

  const flushParagraph = () => {
    if (currentParagraphLines.length > 0) {
      const p = currentParagraphLines.join('\n').trim()
      if (p) outputBlocks.push({ type: 'text', content: p })
      currentParagraphLines = []
    }
  }

  const flushChat = () => {
    if (currentChatItems.length > 0) {
      outputBlocks.push({ type: 'chat', items: [...currentChatItems] })
      currentChatItems = []
    }
  }

  for (const line of lines) {
    const chatItem = tryParseChatLine(line)
    if (chatItem) {
      flushParagraph()
      currentChatItems.push(chatItem)
    } else {
      if (line.trim() === '') {
        flushParagraph()
        flushChat()
      } else {
        flushChat()
        currentParagraphLines.push(line)
      }
    }
  }

  flushParagraph()
  flushChat()
}
