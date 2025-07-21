"""
Test script to demonstrate the new image management logic
"""

def test_image_logic():
    """Test the image management logic with various scenarios"""
    
    def simulate_image_update(existing_images, new_images):
        """Simulate the image update logic"""
        num_existing = len(existing_images)
        num_new_images = len(new_images)
        total_after_adding = num_existing + num_new_images
        
        print(f"Existing: {num_existing}, New: {num_new_images}, Total would be: {total_after_adding}")
        
        # Determine how many existing images to keep/delete
        if total_after_adding <= 5:
            # Case 1: Total ≤ 5, keep all existing images and add new ones
            images_to_delete = []
            remaining_images = existing_images.copy()
            print(f"✅ Keep all {num_existing} existing images, add {num_new_images} new ones")
        else:
            # Case 2: Total > 5, delete oldest images to make room
            num_to_delete = total_after_adding - 5
            images_to_delete = existing_images[:num_to_delete]
            remaining_images = existing_images[num_to_delete:]
            print(f"🗑️  Delete {num_to_delete} oldest images, keep {len(remaining_images)} existing, add {num_new_images} new")
        
        # Final result
        final_images = remaining_images + new_images
        print(f"Final result: {len(final_images)} images total")
        print(f"Deleted: {images_to_delete}")
        print(f"Kept: {remaining_images}")
        print(f"Added: {new_images}")
        print(f"Final: {final_images}")
        print("-" * 50)
        
        return final_images
    
    # Test scenarios
    print("🧪 Testing Image Management Logic\n")
    
    # Scenario 1: 2 existing + 3 new = 5 total (keep all)
    print("Scenario 1: 2 existing + 3 new")
    existing = ["img1.jpg", "img2.jpg"]
    new = ["new1.jpg", "new2.jpg", "new3.jpg"]
    simulate_image_update(existing, new)
    
    # Scenario 2: 2 existing + 4 new = 6 total (delete 1 oldest)
    print("Scenario 2: 2 existing + 4 new")
    existing = ["img1.jpg", "img2.jpg"]
    new = ["new1.jpg", "new2.jpg", "new3.jpg", "new4.jpg"]
    simulate_image_update(existing, new)
    
    # Scenario 3: 5 existing + 2 new = 7 total (delete 2 oldest)
    print("Scenario 3: 5 existing + 2 new")
    existing = ["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg", "img5.jpg"]
    new = ["new1.jpg", "new2.jpg"]
    simulate_image_update(existing, new)
    
    # Scenario 4: 1 existing + 2 new = 3 total (keep all)
    print("Scenario 4: 1 existing + 2 new")
    existing = ["img1.jpg"]
    new = ["new1.jpg", "new2.jpg"]
    simulate_image_update(existing, new)
    
    # Scenario 5: 3 existing + 5 new = 8 total (delete 3 oldest)
    print("Scenario 5: 3 existing + 5 new")
    existing = ["img1.jpg", "img2.jpg", "img3.jpg"]
    new = ["new1.jpg", "new2.jpg", "new3.jpg", "new4.jpg", "new5.jpg"]
    simulate_image_update(existing, new)

if __name__ == "__main__":
    test_image_logic()