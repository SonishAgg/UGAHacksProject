import requests
import json
import re
import time
import sys
import io


def setup_unicode_fix():
    """Fix Unicode encoding for Windows/VS Code"""
    if sys.platform == "win32":
        # Set UTF-8 encoding for stdout
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
        
        # Fix stderr
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

# Call it at the start
setup_unicode_fix()

# Helper function for safe printing
def safe_print(text, end='\n'):
    """Print text with Unicode handling"""
    try:
        print(text, end=end)
    except UnicodeEncodeError:
        # Fallback: encode with UTF-8, ignore errors
        encoded = str(text).encode('utf-8', errors='ignore').decode('utf-8')
        print(encoded, end=end)

url = 'https://graphql.anilist.co'

def clean_description(desc):
    """Clean HTML tags from description"""
    if not desc:
        return ""
    return re.sub('<.*?>', '', desc)

def get_all_media_with_retry(media_type="ANIME", max_items=500, per_page=50):
    """
    Fetch anime or manga with pagination and rate limiting
    Uses exponential backoff for retries
    """
    all_media = []
    page = 1
    has_next_page = True
    total_fetched = 0
    retry_count = 0
    max_retries = 5
    
    safe_print(f"\nStarting to fetch {max_items} {media_type.lower()} items...")
    safe_print("Rate limiting: ~1.5 requests/second to avoid API limits")
    
    start_time = time.time()
    
    while has_next_page and total_fetched < max_items:
        query = '''
        query ($page: Int, $perPage: Int, $type: MediaType) {
            Page(page: $page, perPage: $perPage) {
                pageInfo {
                    total
                    perPage
                    currentPage
                    lastPage
                    hasNextPage
                }
                media(type: $type, sort: POPULARITY_DESC) {
                    id
                    title {
                        english
                    }
                    description
                    episodes
                    chapters
                    status
                    averageScore
                    popularity
                    genres
                    format
                    tags {
                        name
                        description
                        category
                        rank
                     }
                }
            }
        }
        '''
        
        variables = {
            'page': page,
            'perPage': per_page,
            'type': media_type
        }
        
        try:
            # Add delay between requests to respect rate limits
            # AniList allows ~90 requests/minute = ~1.5 requests/second
            if page > 1:
                time.sleep(0.8)  # 800ms delay = ~1.25 requests/second
            
            response = requests.post(url, json={'query': query, 'variables': variables})
            
            # Check for rate limit
            if response.status_code == 429:  # Too Many Requests
                safe_print(f"Rate limited! Waiting 30 seconds... (Page {page})")
                time.sleep(30)
                continue
            
            data = response.json()
            
            if 'errors' in data:
                error_msg = data['errors'][0]['message']
                safe_print(f"API Error on page {page}: {error_msg}")
                
                if "Too Many Requests" in error_msg:
                    safe_print("Rate limit hit. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                else:
                    break
            
            page_info = data['data']['Page']['pageInfo']
            media_list = data['data']['Page']['media']
            
            # Calculate how many items to add
            remaining = max_items - total_fetched
            items_to_add = min(len(media_list), remaining)
            
            if items_to_add > 0:
                all_media.extend(media_list[:items_to_add])
                total_fetched += items_to_add
            
            # Progress indicator
            elapsed = time.time() - start_time
            items_per_second = total_fetched / elapsed if elapsed > 0 else 0
            
            safe_print(f"Page {page}: Fetched {items_to_add} items | "
                      f"Total: {total_fetched}/{max_items} | "
                      f"Speed: {items_per_second:.2f} items/sec")
            
            has_next_page = page_info['hasNextPage'] and total_fetched < max_items
            page += 1
            
            # Reset retry count on successful request
            retry_count = 0
                
        except requests.exceptions.RequestException as e:
            safe_print(f"Network error on page {page}: {e}")
            retry_count += 1
            
            if retry_count >= max_retries:
                safe_print(f"Max retries ({max_retries}) exceeded. Stopping.")
                break
            
            # Exponential backoff
            wait_time = 2 ** retry_count
            safe_print(f"Retrying in {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
            time.sleep(wait_time)
            continue
        
        except Exception as e:
            safe_print(f"Unexpected error on page {page}: {e}")
            break
    
    elapsed_total = time.time() - start_time
    safe_print(f"\n✓ Completed! Fetched {len(all_media)} {media_type.lower()} items in {elapsed_total/60:.1f} minutes")
    
    return all_media

def print_media_info(media_list, media_type="Anime"):
    """Print media information in the requested format"""
    print(f"\n{'='*80}")
    print(f"{media_type.upper()} LIST ({len(media_list)} items)")
    print('='*80)
    
    for i, media in enumerate(media_list, 1):
        print(f"\n{'='*60}")
        print(f"ITEM {i}:")
        print('='*60)
        print(f"ID: {media['id']}")
        print(f"Title (Romaji): {media['title']['romaji']}")
        print(f"Title (English): {media['title']['english']}")
        print(f"Format: {media.get('format', 'N/A')}")
        print(f"Status: {media['status']}")
        
        if media_type.lower() == "anime":
            print(f"Episodes: {media.get('episodes', 'N/A')}")
        else:
            print(f"Chapters: {media.get('chapters', 'N/A')}")
        
        print(f"Average Score: {media.get('averageScore', 'N/A')}/100")
        print(f"Popularity: {media.get('popularity', 'N/A')}")
        print(f"Genres: {', '.join(media.get('genres', []))}")
        
        if media['description']:
            clean_desc = clean_description(media['description'])
            # Limit description length
            if len(clean_desc) > 300:
                clean_desc = clean_desc[:300] + "..."
            print(f"Description: {clean_desc}")
        else:
            print("Description: No description available")
        
        if 'tags' in media and media['tags']:
            # Get top 5 tags by rank
            sorted_tags = sorted(media['tags'], key=lambda x: x.get('rank', 0), reverse=True)
            top_tags = [tag['name'] for tag in sorted_tags[:5]]
            print(f"Top Tags: {', '.join(top_tags)}")
            
            # Optional: Print tag details
            print(f"Total Tags: {len(media['tags'])}")
        else:
            print("Tags: No tags available")

        
    
    print(f"\n{'='*80}")
    print(f"Total {media_type}s: {len(media_list)}")
    print('='*80)

def save_to_json(media_list, filename):
    """Save media list to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(media_list, f, ensure_ascii=False, indent=2)
    print(f"\nData saved to {filename}")

# Main execution
if __name__ == "__main__":
    # Fetch anime (first 100 items as example)
    print("Fetching anime...")
    anime_list = get_all_media_with_retry(media_type="ANIME", max_items=1500, per_page=50)
    
    # Print anime info
    print_media_info(anime_list, "Anime")
    
    # Save to file
    save_to_json(anime_list, "anime_list.json")
    
    # Uncomment to fetch manga too
    print("\n\nFetching manga...")
    manga_list = get_all_media_with_retry(media_type="MANGA", max_items=1500, per_page=50)
    
    # Print manga info
    print_media_info(manga_list, "Manga")
    
    # Save to file
    save_to_json(manga_list, "manga_list.json")