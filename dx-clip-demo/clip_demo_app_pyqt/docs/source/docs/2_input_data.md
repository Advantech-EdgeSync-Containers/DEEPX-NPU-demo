# Sample Input Data 

## Video Input

The demo app is configured to handle 16 videos located in `assets/demo_videos/*.mp4 or *.mov`. This configuration is managed in JSON format in the `clip_demo_app_pyqt/data/default_data.json` file.

```json
{
  "video_path_lists": [
    [
      "demo_videos/burning_car"
    ],
    [
      "demo_videos/crowded_subway_platform"
    ],
    ...
  ]
}
```

## Text Input

Each video is associated with 26 sentences, along with the corresponding `score_min`, `score_max`, and `score_threshold` values. This data is also managed in JSON format in the `clip_demo_app_pyqt/data/default_data.json` file.

```json
{
  "video_path_lists": [
    [
      "demo_videos/burning_car"
    ],
    [
      "demo_videos/crowded_subway_platform"
    ],
    ...
  ],
  ...
  "sentence_list": [
    {
        "text": "Fire is coming out of the car",
        "min_score": 0.23,
        "max_score": 0.26,
        "threshold": 0.24,
        ...
    },
    {
        "text": "The car is exploding",
        "min_score": 0.24,
        "max_score": 0.28,
        "threshold": 0.26,
        ...
    },
    ...
    
    {
      "text": "The subway is crowded with people",
      "score_min": 0.27,
      "score_max": 0.29,
      "score_threshold": 0.28,
      ...
    },
    {
      "text": "People is crowded in the subway",
      "score_min": 0.27,
      "score_max": 0.29,
      "score_threshold": 0.28,
      ...
    }
    ...
  ]
}
```
