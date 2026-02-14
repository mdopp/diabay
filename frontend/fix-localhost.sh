#!/bin/bash
# Script to replace all localhost references with dynamic URLs

cd /home/mdopp/coding/diabay/frontend/src

# Add import where needed and replace localhost URLs
files=(
  "pages/DuplicatesPage.tsx"
  "pages/ImageDetailPage.tsx"
  "components/features/viewer/PresetComparison.tsx"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "Processing $file..."
    # Add import if not exists
    if ! grep -q "import.*getAssetUrl.*from.*@/lib/api/client" "$file"; then
      sed -i "1i import { API_URL, getAssetUrl } from '@/lib/api/client'" "$file"
    fi

    # Replace localhost URLs
    sed -i "s|http://localhost:8000/\${|`${API_URL}/|g" "$file"
    sed -i "s|http://localhost:8000\${|`${API_URL}|g" "$file"
    sed -i "s|'http://localhost:8000/api|\`\${API_URL}/api|g" "$file"
    sed -i "s|'http://localhost:8000/\${|\`\${API_URL}/\${|g" "$file"
  fi
done

echo "Done!"
