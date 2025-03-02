import unittest
from unittest.mock import patch, MagicMock
import wp_word_freq

sample_texts = {
    'Python' : "Python python is programming programming programming",
    'Programming' : "Programming is creating creating"
}

class TestWikipediaAPI(unittest.TestCase):
    
    @patch('wikipediaapi.Wikipedia.page')
    def test_get_word_frequencies(self, mock_page):
        """Test that words are counted correctly"""
        mock_page.return_value.exists.return_value = True
        mock_page.return_value.text = sample_texts['Python']
        mock_page.return_value.links = {}
        
        result = wp_word_freq.get_word_frequencies("Python", 0)
        self.assertEqual(result["python"], 2)
        self.assertEqual(result["is"], 1)
        self.assertEqual(result["programming"], 3)


    @patch('wikipediaapi.Wikipedia.page')
    def test_get_word_frequencies_with_links(self, mock_page):
        """Test that linked articles are followed correctly."""
        def mock_wiki_page(title):
            mock_page = MagicMock()
            mock_page.exists.return_value = True
            if title == "Python":
                mock_page.text = sample_texts['Python']
                mock_page.links = {"Programming": None}
            elif title == "Programming":
                mock_page.text = sample_texts['Programming']
                mock_page.links = {}
            return mock_page
        
        mock_page.side_effect = mock_wiki_page
        
        result = wp_word_freq.get_word_frequencies("Python", 1)
        self.assertEqual(result["python"], 2)
        self.assertEqual(result["is"], 2)
        self.assertEqual(result["programming"], 4)
        self.assertEqual(result["creating"], 2)
        

    def test_clean_text(self):
        text = "Hello, world! 420-watt high-speed 3.14 test."
        cleaned = wp_word_freq.clean_text(text)
        self.assertEqual(cleaned, ["hello", "world", "420-watt", "high-speed", "3.14", "test"])

    def test_get_word_frequencies_route(self):
        with wp_word_freq.app.test_client() as client:
            response = client.get('/get_word_frequencies?title=Python&depth=0')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIsInstance(data, dict)

    def test_post_frequencies(self):
        with wp_word_freq.app.test_client() as client:
            response = client.post('/keywords', json={
                'article': sample_texts['Python'],
                'depth': 0,
                'ignore_list': ["is"],
                'percentile': 0
            })
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIsInstance(data, dict)
            self.assertIn("python", data)
            self.assertNotIn("is", data)
            for _, details in data.items():
                self.assertIn("count", details)
                self.assertIn("percentage", details)
                self.assertGreaterEqual(details["percentage"], 0)
                self.assertLessEqual(details["percentage"], 100)

if __name__ == '__main__':
    unittest.main()