import { useId, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import {
  FilePlus,
  FolderPen,
  MoreHorizontal,
  Pin,
  Tag,
  Trash2,
  X,
} from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "darkraise-ui/components/dropdown-menu"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { toast } from "darkraise-ui/components/sonner"
import { Switch } from "darkraise-ui/components/switch"
import {
  TagsInput,
  TagsInputControl,
  TagsInputInput,
  TagsInputItem,
  TagsInputItemDeleteTrigger,
  TagsInputItemPreview,
  TagsInputItemText,
} from "darkraise-ui/components/tags-input"
import { Textarea } from "darkraise-ui/components/textarea"
import {
  isUriTaken,
  useDocumentCreate,
  useDocumentMetadataUpdate,
  useDocumentSubtreeDelete,
  useDocumentBlocks,
  useDocumentSubtreeRename,
  type DocumentListItem,
} from "@/hooks/api"
import type { MoveTarget } from "../move-target"
import type { UriTreeNode } from "../uri-tree"
import { checkSubtree, documentWriteMessage, uriProblem } from "../subtree"

/** Pinned state and tags, beside the open document's path. Rendered from
 *  the list row, so a Details save shows here as soon as the list refetches. */
export function DocumentBadges({ document }: { document: DocumentListItem }) {
  const tags = document.tags ?? []
  if (!document.pinned_at && tags.length === 0) return null
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1">
      {document.pinned_at ? (
        <Badge variant="outline" className="gap-1 text-xs">
          <Pin aria-hidden className="size-3" />
          Pinned
        </Badge>
      ) : null}
      {tags.map((tag) => (
        <Badge key={tag} variant="secondary" className="gap-1 text-xs">
          <Tag aria-hidden className="size-3" />
          {tag}
        </Badge>
      ))}
    </div>
  )
}

function TagsField({
  labelId,
  tags,
  onChange,
}: {
  labelId: string
  tags: string[]
  onChange: (tags: string[]) => void
}) {
  return (
    <TagsInput value={tags} onValueChange={({ value }) => onChange(value)}>
      <TagsInputControl>
        {tags.map((tag, index) => (
          <TagsInputItem key={tag} index={index} value={tag}>
            <TagsInputItemPreview>
              <TagsInputItemText>{tag}</TagsInputItemText>
              <TagsInputItemDeleteTrigger aria-label={`Remove ${tag}`}>
                <X aria-hidden className="size-3" />
              </TagsInputItemDeleteTrigger>
            </TagsInputItemPreview>
          </TagsInputItem>
        ))}
        <TagsInputInput
          aria-labelledby={labelId}
          placeholder={tags.length === 0 ? "Add tags…" : ""}
        />
      </TagsInputControl>
    </TagsInput>
  )
}

const sameTags = (a: string[], b: string[]) =>
  a.length === b.length && a.every((t, i) => t === b[i])

/** Title, path, pin and tags through the metadata PATCH, sending only the
 *  fields that changed (an unnamed field is left alone by the server, and a
 *  call naming none is a 422). */
export function DocumentDetailsDialog({
  document,
  open,
  onOpenChange,
}: {
  document: DocumentListItem
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {/* Mounted per opening, so the fields start from the current row
            rather than from whatever the last opening left behind. */}
        {open ? (
          <DetailsForm document={document} onDone={() => onOpenChange(false)} />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

function DetailsForm({
  document,
  onDone,
}: {
  document: DocumentListItem
  onDone: () => void
}) {
  const qc = useQueryClient()
  const update = useDocumentMetadataUpdate()
  // A move carries the hash as of this dialog's opening (the reader's cache
  // entry, refreshed on mount): it is the one metadata edit whose meaning
  // depends on content, so moving a document re-filed meanwhile is refused
  // rather than carrying along text nobody here has seen. Title, pin and
  // tags apply whatever the content.
  const blocks = useDocumentBlocks(document.id)
  const [title, setTitle] = useState(document.title ?? "")
  const [uri, setUri] = useState(document.uri ?? "")
  const [pinned, setPinned] = useState(Boolean(document.pinned_at))
  const initialTags = [...(document.tags ?? [])].sort()
  const [tags, setTags] = useState(initialTags)
  const [problem, setProblem] = useState<string | null>(null)
  const ids = { title: useId(), uri: useId(), pinned: useId(), tags: useId() }

  const trimmedUri = uri.trim()
  const uriChanged = trimmedUri !== (document.uri ?? "")
  const titleChanged = title.trim() !== (document.title ?? "")
  const pinChanged = pinned !== Boolean(document.pinned_at)
  const sortedTags = [...tags].sort()
  const tagsChanged = !sameTags(sortedTags, initialTags)
  const dirty = uriChanged || titleChanged || pinChanged || tagsChanged

  const submit = () => {
    if (uriChanged) {
      const bad = uriProblem(trimmedUri)
      if (bad) return setProblem(bad)
    }
    if (titleChanged && !title.trim()) return setProblem("Enter a title.")
    update.mutate(
      {
        documentId: document.id,
        ...(titleChanged ? { title: title.trim() } : {}),
        ...(uriChanged ? { uri: trimmedUri } : {}),
        ...(pinChanged ? { pinned } : {}),
        ...(tagsChanged ? { tags: sortedTags } : {}),
        ...(uriChanged && blocks.data?.content_hash
          ? { expected_hash: blocks.data.content_hash }
          : {}),
      },
      {
        onSuccess: () => {
          toast.success("Details saved")
          onDone()
        },
        onError: (error) => {
          // A stale hash is resolved by a re-read, so the next save
          // preconditions on the document as it is now.
          void qc.invalidateQueries({
            queryKey: ["documentBlocks", document.id],
          })
          setProblem(documentWriteMessage(error))
        },
      },
    )
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <DialogHeader>
        <DialogTitle>Document details</DialogTitle>
        <DialogDescription>
          Changing the path moves the document in the tree.
        </DialogDescription>
      </DialogHeader>
      <div className="space-y-1.5">
        <Label htmlFor={ids.title}>Title</Label>
        <Input
          id={ids.title}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor={ids.uri}>Path</Label>
        <Input
          id={ids.uri}
          value={uri}
          onChange={(e) => {
            setUri(e.target.value)
            setProblem(null)
          }}
          className="font-mono"
        />
      </div>
      <div className="flex items-center justify-between gap-3">
        <Label htmlFor={ids.pinned}>Pinned</Label>
        <Switch id={ids.pinned} checked={pinned} onCheckedChange={setPinned} />
      </div>
      <div className="space-y-1.5">
        <Label id={ids.tags}>Tags</Label>
        <TagsField labelId={ids.tags} tags={tags} onChange={setTags} />
      </div>
      {problem ? (
        <p role="alert" className="text-destructive text-sm">
          {problem}
        </p>
      ) : null}
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={!dirty || update.isPending}>
          {update.isPending ? "Saving…" : "Save"}
        </Button>
      </DialogFooter>
    </form>
  )
}

/** File a new markdown document at a path no document holds.
 *
 *  `POST /documents` is an upsert on `(project, uri)`: aimed at a taken path
 *  it would silently replace that document's content. So a taken path is
 *  refused twice before the POST -- against the loaded list, then against
 *  the server (the list may predate a mirror's filing) -- and an outcome
 *  other than `created` is still reported rather than called a creation. */
export function NewDocumentDialog({
  project,
  items,
  open,
  initialUri,
  onOpenChange,
  onCreated,
}: {
  project: string
  items: DocumentListItem[]
  open: boolean
  initialUri: string
  onOpenChange: (open: boolean) => void
  onCreated: (documentId: string) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open ? (
          <NewDocumentForm
            project={project}
            items={items}
            initialUri={initialUri}
            onCancel={() => onOpenChange(false)}
            onCreated={(id) => {
              onOpenChange(false)
              onCreated(id)
            }}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

function NewDocumentForm({
  project,
  items,
  initialUri,
  onCancel,
  onCreated,
}: {
  project: string
  items: DocumentListItem[]
  initialUri: string
  onCancel: () => void
  onCreated: (documentId: string) => void
}) {
  const create = useDocumentCreate()
  const [uri, setUri] = useState(initialUri)
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")
  const [problem, setProblem] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)
  const ids = { uri: useId(), title: useId(), content: useId() }

  const taken = (path: string) =>
    `A document is already filed at ${path}. Open it from the tree, or choose another path.`

  const submit = async () => {
    const path = uri.trim()
    const bad = uriProblem(path)
    if (bad) return setProblem(bad)
    if (items.some((d) => d.uri === path)) return setProblem(taken(path))
    setChecking(true)
    try {
      if (await isUriTaken(project, path)) return setProblem(taken(path))
    } catch (error) {
      return setProblem(documentWriteMessage(error))
    } finally {
      setChecking(false)
    }
    const name = title.trim() || path.split("/").pop() || path
    create.mutate(
      { project, uri: path, title: name, content },
      {
        onSuccess: ({ document_id, outcome }) => {
          if (outcome === "created") {
            toast.success(`Filed ${path}`)
          } else {
            // Lost a race with another filing at the same path. Its earlier
            // content survives as a revision.
            toast.error(
              `Another filing reached ${path} first; this content replaced it. Its earlier version is under Revisions.`,
            )
          }
          onCreated(document_id)
        },
        onError: (error) => setProblem(documentWriteMessage(error)),
      },
    )
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault()
        void submit()
      }}
    >
      <DialogHeader>
        <DialogTitle>New document</DialogTitle>
        <DialogDescription>Filed as markdown into {project}.</DialogDescription>
      </DialogHeader>
      <div className="space-y-1.5">
        <Label htmlFor={ids.uri}>Path</Label>
        <Input
          id={ids.uri}
          autoFocus
          value={uri}
          placeholder="notes/new-document.md"
          onChange={(e) => {
            setUri(e.target.value)
            setProblem(null)
          }}
          className="font-mono"
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor={ids.title}>Title</Label>
        <Input
          id={ids.title}
          value={title}
          placeholder="Defaults to the file name"
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor={ids.content}>Content</Label>
        <Textarea
          id={ids.content}
          rows={8}
          value={content}
          placeholder="# Heading&#10;&#10;Markdown. Leave empty to start from the title."
          onChange={(e) => setContent(e.target.value)}
          className="font-mono text-sm"
        />
      </div>
      {problem ? (
        <p role="alert" className="text-destructive text-sm">
          {problem}
        </p>
      ) : null}
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={checking || create.isPending}>
          {checking || create.isPending ? "Filing…" : "Create"}
        </Button>
      </DialogFooter>
    </form>
  )
}

/** A folder row's menu. Stops propagation for the reason the page tree's
 *  does: React events bubble out of the portal, and the row would toggle. */
export function FolderActions({
  node,
  onNewHere,
  onRename,
  onDelete,
}: {
  node: UriTreeNode
  onNewHere: (folder: string) => void
  onRename: (node: UriTreeNode) => void
  onDelete: (node: UriTreeNode) => void
}) {
  return (
    <span className="ml-auto flex shrink-0 items-center opacity-0 group-hover:opacity-100 focus-within:opacity-100 [@media(hover:none)]:opacity-100">
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={`Actions for ${node.path}`}
          className="text-muted-foreground hover:text-foreground rounded p-0.5"
          onClick={(event) => event.stopPropagation()}
          onKeyDown={(event) => event.stopPropagation()}
        >
          <MoreHorizontal aria-hidden className="size-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="end"
          onClick={(event) => event.stopPropagation()}
        >
          <DropdownMenuItem onSelect={() => onNewHere(node.path)}>
            <FilePlus aria-hidden className="mr-2 size-3.5" />
            New document here
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => onRename(node)}>
            <FolderPen aria-hidden className="mr-2 size-3.5" />
            Rename folder
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive focus:text-destructive data-[highlighted]:text-destructive"
            onSelect={() => onDelete(node)}
          >
            <Trash2 aria-hidden className="mr-2 size-3.5" />
            Delete folder
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </span>
  )
}

/** Rewrite a folder's path across every document under it, in one
 *  transaction: a collision refuses the whole rename. */
export function RenameFolderDialog({
  project,
  items,
  node,
  onClose,
}: {
  project: string
  items: DocumentListItem[]
  node: UriTreeNode | null
  onClose: () => void
}) {
  return (
    <Dialog open={node !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        {node ? (
          <RenameFolderForm
            project={project}
            items={items}
            node={node}
            onClose={onClose}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

function RenameFolderForm({
  project,
  items,
  node,
  onClose,
}: {
  project: string
  items: DocumentListItem[]
  node: UriTreeNode
  onClose: () => void
}) {
  const rename = useDocumentSubtreeRename()
  const [next, setNext] = useState(node.path)
  const [problem, setProblem] = useState<string | null>(null)
  const id = useId()
  const check = checkSubtree(node, items)

  const submit = () => {
    const path = next.trim()
    const bad = uriProblem(path)
    if (bad) return setProblem(bad)
    if (path === node.path) return onClose()
    rename.mutate(
      { project, uri_prefix: node.path, new_uri_prefix: path },
      {
        onSuccess: ({ renamed }) => {
          toast.success(
            `Moved ${renamed} ${renamed === 1 ? "document" : "documents"} to ${path}`,
          )
          onClose()
        },
        onError: (error) => setProblem(documentWriteMessage(error)),
      },
    )
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <DialogHeader>
        <DialogTitle>Rename folder {node.path}</DialogTitle>
        <DialogDescription>
          {check.ok
            ? `Every document under it moves with it (${check.count}).`
            : check.reason}
        </DialogDescription>
      </DialogHeader>
      <Label htmlFor={id} className="sr-only">
        New folder path
      </Label>
      <Input
        id={id}
        autoFocus
        aria-label="New folder path"
        value={next}
        onFocus={(e) => e.currentTarget.select()}
        onChange={(e) => {
          setNext(e.target.value)
          setProblem(null)
        }}
        className="font-mono"
        disabled={!check.ok}
      />
      {problem ? (
        <p role="alert" className="text-destructive text-sm">
          {problem}
        </p>
      ) : null}
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={!check.ok || rename.isPending}>
          Rename
        </Button>
      </DialogFooter>
    </form>
  )
}

export function DeleteFolderDialog({
  project,
  items,
  node,
  onClose,
}: {
  project: string
  items: DocumentListItem[]
  node: UriTreeNode | null
  onClose: () => void
}) {
  const remove = useDocumentSubtreeDelete()
  const check = node ? checkSubtree(node, items) : null
  return (
    <AlertDialog
      open={node !== null}
      onOpenChange={(open) => !open && onClose()}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete the folder {node?.path}?</AlertDialogTitle>
          <AlertDialogDescription>
            {check?.ok
              ? `This deletes ${check.count} ${check.count === 1 ? "document" : "documents"} under ${node?.path}, with their revisions. It cannot be undone.`
              : check?.reason}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          {check?.ok && node ? (
            <AlertDialogAction
              // The library hard-codes the primary variant; a delete is
              // destructive (the same override DocumentActions uses).
              data-variant="destructive"
              onClick={() =>
                remove.mutate(
                  { project, uri_prefix: node.path },
                  {
                    onSuccess: ({ deleted }) => {
                      toast.success(
                        `Deleted ${deleted} ${deleted === 1 ? "document" : "documents"}`,
                      )
                      onClose()
                    },
                    onError: (error) =>
                      toast.error(
                        `The folder could not be deleted — ${documentWriteMessage(error)}`,
                      ),
                  },
                )
              }
            >
              Delete {check.count}{" "}
              {check.count === 1 ? "document" : "documents"}
            </AlertDialogAction>
          ) : null}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

/** What a drop in the tree does: a document moves by the metadata PATCH, a
 *  folder by the subtree rename -- after the same addressability check the
 *  folder menu makes. */
export function useMoveDocuments(
  project: string,
  items: DocumentListItem[],
  byPath: (path: string) => UriTreeNode | undefined,
) {
  const update = useDocumentMetadataUpdate()
  const rename = useDocumentSubtreeRename()
  return (target: MoveTarget) => {
    if (target.kind === "document") {
      update.mutate(
        { documentId: target.documentId, uri: target.uri },
        {
          onSuccess: () => toast.success(`Moved to ${target.uri}`),
          onError: (error) => toast.error(documentWriteMessage(error)),
        },
      )
      return
    }
    const node = byPath(target.uriPrefix)
    const check = node ? checkSubtree(node, items) : null
    if (!check?.ok) {
      toast.error(check?.reason ?? `${target.uriPrefix} is not in the tree.`)
      return
    }
    rename.mutate(
      {
        project,
        uri_prefix: target.uriPrefix,
        new_uri_prefix: target.newUriPrefix,
      },
      {
        onSuccess: ({ renamed }) =>
          toast.success(
            `Moved ${renamed} ${renamed === 1 ? "document" : "documents"} to ${target.newUriPrefix}`,
          ),
        onError: (error) => toast.error(documentWriteMessage(error)),
      },
    )
  }
}
