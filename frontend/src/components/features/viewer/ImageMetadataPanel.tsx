import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { ImageDetail } from '@/types/image'
import { Calendar, Image as ImageIcon, Clock, Plus, X } from 'lucide-react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

interface ImageMetadataPanelProps {
  image: ImageDetail
}

/**
 * Metadata sidebar showing image details, tags, and EXIF
 */
export function ImageMetadataPanel({ image }: ImageMetadataPanelProps) {
  const [newTag, setNewTag] = useState('')
  const [isAddingTag, setIsAddingTag] = useState(false)
  const queryClient = useQueryClient()

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // Add tag mutation
  const addTagMutation = useMutation({
    mutationFn: async (tag: string) => {
      await apiClient.post(`/api/images/${image.id}/tags`, {
        tag,
        category: 'user',
        confidence: 1.0
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image', image.id] })
      setNewTag('')
      setIsAddingTag(false)
    }
  })

  // Remove tag mutation
  const removeTagMutation = useMutation({
    mutationFn: async (tag: string) => {
      await apiClient.delete(`/api/images/${image.id}/tags/${encodeURIComponent(tag)}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image', image.id] })
    }
  })

  const handleAddTag = () => {
    if (newTag.trim()) {
      addTagMutation.mutate(newTag.trim())
    }
  }

  const handleRemoveTag = (tag: string) => {
    removeTagMutation.mutate(tag)
  }

  return (
    <div className="p-4">
      {/* Horizontal layout on desktop */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Basic Info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Image Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
          <div className="flex items-start gap-2">
            <ImageIcon className="w-4 h-4 text-muted-foreground mt-0.5" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Filename</p>
              <p className="font-mono text-xs break-all">{image.filename}</p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <ImageIcon className="w-4 h-4 text-muted-foreground mt-0.5" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Dimensions</p>
              <p>{image.width} × {image.height}</p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground mt-0.5" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Created</p>
              <p className="text-xs">{formatDate(image.created_at)}</p>
            </div>
          </div>

          {image.processed_at && (
            <div className="flex items-start gap-2">
              <Clock className="w-4 h-4 text-muted-foreground mt-0.5" />
              <div className="flex-1">
                <p className="text-xs text-muted-foreground">Processed</p>
                <p className="text-xs">{formatDate(image.processed_at)}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Enhancement Parameters */}
      {image.enhancement_params && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Enhancement</CardTitle>
            <CardDescription className="text-xs">Processing parameters</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Histogram Clip:</span>
              <span className="font-medium">{image.enhancement_params.histogram_clip}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">CLAHE Clip:</span>
              <span className="font-medium">{image.enhancement_params.clahe_clip}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Face Detected:</span>
              <Badge variant={image.enhancement_params.face_detected ? 'default' : 'secondary'} className="h-5">
                {image.enhancement_params.face_detected ? 'Yes' : 'No'}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tags */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Tags</CardTitle>
              <CardDescription className="text-xs">AI-detected & user tags</CardDescription>
            </div>
            {!isAddingTag && (
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7"
                onClick={() => setIsAddingTag(true)}
                title="Add tag"
              >
                <Plus className="w-4 h-4" />
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Existing tags */}
          {image.tags && image.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {image.tags.map((tag, index) => (
                <Badge
                  key={index}
                  variant="outline"
                  className="text-xs group relative pr-6"
                  title={`Source: ${tag.source} | Confidence: ${tag.confidence?.toFixed(2) || 'N/A'}`}
                >
                  {tag.tag}
                  {tag.source === 'manual' && (
                    <button
                      className="absolute right-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleRemoveTag(tag.tag)}
                      disabled={removeTagMutation.isPending}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </Badge>
              ))}
            </div>
          )}

          {/* Add tag input */}
          {isAddingTag && (
            <div className="flex gap-2">
              <Input
                type="text"
                placeholder="Enter tag..."
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAddTag()
                  if (e.key === 'Escape') setIsAddingTag(false)
                }}
                className="h-8 text-sm"
                autoFocus
                disabled={addTagMutation.isPending}
              />
              <Button
                size="sm"
                onClick={handleAddTag}
                disabled={!newTag.trim() || addTagMutation.isPending}
                className="h-8"
              >
                Add
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setNewTag('')
                  setIsAddingTag(false)
                }}
                className="h-8"
              >
                Cancel
              </Button>
            </div>
          )}

          {/* Empty state */}
          {(!image.tags || image.tags.length === 0) && !isAddingTag && (
            <p className="text-xs text-muted-foreground">No tags yet. Click + to add one.</p>
          )}
        </CardContent>
      </Card>
      </div>
    </div>
  )
}
