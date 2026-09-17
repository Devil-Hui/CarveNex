/**
 * 首页「应用场景视频画廊」数据清单 —— 由 scripts/gen-scenario-manifest.cjs 自动生成，请勿手改。
 * 视频源：public/videos/laserpeck 文件夹，由 Vite/nginx 静态服务到 /videos/laserpeck/。
 */
export interface ScenarioVideo {
  id: string
  title: string
  url: string
}

export interface ScenarioCategory {
  id: string
  /** 分类展示名（≤20 字） */
  name: string
  /** 分类一句话说明（≤20 字） */
  desc: string
  videos: ScenarioVideo[]
}

export interface ScenarioRow {
  id: string
  /** 行展示名（上行=雕刻材料，下行=使用场景） */
  name: string
  categories: ScenarioCategory[]
}

export const SCENARIO_ROWS: ScenarioRow[] = [
  {
    "id": "materials",
    "name": "Materials",
    "categories": [
      {
        "id": "featured",
        "name": "Featured",
        "desc": "All-in-one scenes",
        "videos": [
          {
            "id": "video-0",
            "title": "多场景应用",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E5%A4%9A%E5%9C%BA%E6%99%AF%E5%BA%94%E7%94%A8.mp4"
          }
        ]
      },
      {
        "id": "video-0",
        "name": "Leather",
        "desc": "Rich grain engraving",
        "videos": [
          {
            "id": "laserpecker-2-lasercut-laserengraving-lasermachi",
            "title": "Laserpecker_2_lasercut_laserengraving_lasermachine_leathercraft_onsitesouvenir_smallbusiness",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99(%E7%9A%AE%E9%9D%A9%EF%BC%89/Laserpecker_2_lasercut_laserengraving_lasermachine_leathercraft_onsitesouvenir_smallbusiness.mp4"
          },
          {
            "id": "personalize-shoes-with-laserpecker-lp5",
            "title": "Personalize_Shoes_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99(%E7%9A%AE%E9%9D%A9%EF%BC%89/Personalize_Shoes_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "the-best-gift-says-we-thought-of-you-engraved-by",
            "title": "The_best_gift_says_we_thought_of_you._Engraved_by_LP4._backtoschool_laserpecker_giftideas",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99(%E7%9A%AE%E9%9D%A9%EF%BC%89/The_best_gift_says_we_thought_of_you._Engraved_by_LP4._backtoschool_laserpecker_giftideas.mp4"
          }
        ]
      },
      {
        "id": "video-1",
        "name": "Plastic",
        "desc": "Done in 10 seconds",
        "videos": [
          {
            "id": "back-to-school-shopping-list-but-make-it-persona",
            "title": "Back_to_school_shopping_list_but_make_it_personal._laserpecker_schoolsupplies",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E5%A1%91%E6%96%99%EF%BC%89/Back_to_school_shopping_list_but_make_it_personal._laserpecker_schoolsupplies.mp4"
          },
          {
            "id": "create-stamp-with-laserpecker-lp5",
            "title": "Create_Stamp_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E5%A1%91%E6%96%99%EF%BC%89/Create_Stamp_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "fast-engraving-on-the-switch-with-laserpecker-lp",
            "title": "Fast_engraving_on_the_switch_with_LaserPecker_LP2",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E5%A1%91%E6%96%99%EF%BC%89/Fast_engraving_on_the_switch_with_LaserPecker_LP2.mp4"
          },
          {
            "id": "video-3",
            "title": "材料（塑料）",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E5%A1%91%E6%96%99%EF%BC%89/%E6%9D%90%E6%96%99%EF%BC%88%E5%A1%91%E6%96%99%EF%BC%89.mp4"
          }
        ]
      },
      {
        "id": "video-2",
        "name": "Fabric",
        "desc": "Soft yet engravable",
        "videos": [
          {
            "id": "create-one-of-a-kind-clothes-with-laserpecker-lp",
            "title": "Create_One-of-a-Kind_Clothes_with_LaserPecker_LP4",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E5%B8%83%E6%96%99)/Create_One-of-a-Kind_Clothes_with_LaserPecker_LP4.mp4"
          },
          {
            "id": "done-in-just-10-seconds-laser-engraving-on-towel",
            "title": "Done_in_Just_10_Seconds_Laser_Engraving_on_Towel_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E5%B8%83%E6%96%99)/Done_in_Just_10_Seconds_Laser_Engraving_on_Towel_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "personalize-towels-with-the-laserpecker-lp4-fast",
            "title": "Personalize_Towels_with_the_LaserPecker_LP4_-_Fast_Easy",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E5%B8%83%E6%96%99)/Personalize_Towels_with_the_LaserPecker_LP4_-_Fast_Easy.mp4"
          },
          {
            "id": "video-3",
            "title": "材料（布料）",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E5%B8%83%E6%96%99)/%E6%9D%90%E6%96%99%EF%BC%88%E5%B8%83%E6%96%99%EF%BC%89.mp4"
          }
        ]
      },
      {
        "id": "video-3",
        "name": "Wood",
        "desc": "Photo & deep carving",
        "videos": [
          {
            "id": "laser-engraving-picture-on-wooden-board-with-las",
            "title": "Laser engraving - Picture on wooden board - with Laser Pecker 2 [S2Gvok4pauc].f137",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E6%9C%A8%E6%9D%90%EF%BC%89/Laser%20engraving%20-%20Picture%20on%20wooden%20board%20-%20with%20Laser%20Pecker%202%20%5BS2Gvok4pauc%5D.f137.mp4"
          },
          {
            "id": "laserpecker-lp1-plus-in-action-fully-upgraded-st",
            "title": "LaserPecker_LP1_Plus_in_Action_Fully_Upgraded_Still_Portable",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E6%9C%A8%E6%9D%90%EF%BC%89/LaserPecker_LP1_Plus_in_Action_Fully_Upgraded_Still_Portable.mp4"
          },
          {
            "id": "laser-engraved-football-field-snack-board-with-l",
            "title": "Laser_Engraved_Football_Field_Snack_Board_with_LaserPecker_LX2",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E6%9C%A8%E6%9D%90%EF%BC%89/Laser_Engraved_Football_Field_Snack_Board_with_LaserPecker_LX2.mp4"
          }
        ]
      },
      {
        "id": "video-4",
        "name": "Glass",
        "desc": "Crisp frosted finish",
        "videos": [
          {
            "id": "customized-coffee-jar-with-laserpecker-lp5",
            "title": "Customized_Coffee_Jar_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E7%8E%BB%E7%92%83%EF%BC%89/Customized_Coffee_Jar_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "glass-engraving-with-laserpecker-lp4-and-rotary-",
            "title": "Glass_engraving_with_LaserPecker_LP4_and_rotary_tool",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E7%8E%BB%E7%92%83%EF%BC%89/Glass_engraving_with_LaserPecker_LP4_and_rotary_tool.mp4"
          }
        ]
      },
      {
        "id": "video-5",
        "name": "Stone",
        "desc": "3D relief on slate",
        "videos": [
          {
            "id": "stone-3d-embossing-with-laserpecker-lp5-1",
            "title": "Stone_3D_Embossing_with_LaserPecker_LP5 (1)",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E6%9D%90%E6%96%99%EF%BC%88%E7%9F%B3%E6%9D%BF%EF%BC%89/Stone_3D_Embossing_with_LaserPecker_LP5%20(1).mp4"
          }
        ]
      },
      {
        "id": "video-6",
        "name": "Metal",
        "desc": "Deep & color marking",
        "videos": [
          {
            "id": "3d-embossing-a-brass-coin-with-the-laserpecker-l",
            "title": "3D_Embossing_a_Brass_Coin_with_the_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/3D_Embossing_a_Brass_Coin_with_the_LaserPecker_LP5.mp4"
          },
          {
            "id": "color-engraving-with-laserpecker-lp4",
            "title": "Color_Engraving_with_LaserPecker_LP4",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/Color_Engraving_with_LaserPecker_LP4.mp4"
          },
          {
            "id": "custom-new-year-theme-turnbler-with-laserpecker-",
            "title": "Custom_New_Year_Theme_Turnbler_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/Custom_New_Year_Theme_Turnbler_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "deep-engraved-buttons-with-laserpecker-lp5",
            "title": "Deep-engraved_Buttons_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/Deep-engraved_Buttons_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "engraving-with-the-laser-pecker-4",
            "title": "Engraving_with_the_Laser_Pecker_4",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/Engraving_with_the_Laser_Pecker_4.mp4"
          },
          {
            "id": "laserpecker-2-custom-engraved-tumbler-diy-engrav",
            "title": "LaserPecker_2_-_custom_engraved_Tumbler._DiY_engraving_full_review_coming_soon",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/LaserPecker_2_-_custom_engraved_Tumbler._DiY_engraving_full_review_coming_soon.mp4"
          },
          {
            "id": "laserpecker-lp2-plus-diy-halloween-cup-that-glow",
            "title": "LaserPecker_LP2_Plus_-_DIY_Halloween_Cup_That_Glows",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/LaserPecker_LP2_Plus_-_DIY_Halloween_Cup_That_Glows.mp4"
          },
          {
            "id": "statue-of-liberty-coin-embossing-with-laserpecke",
            "title": "Statue_of_Liberty_Coin_Embossing_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/Statue_of_Liberty_Coin_Embossing_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "turn-your-favorite-photo-into-embossed-artwork-w",
            "title": "Turn_Your_Favorite_Photo_into_Embossed_Artwork_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/Turn_Your_Favorite_Photo_into_Embossed_Artwork_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "video-9",
            "title": "金属，铝",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/%E9%87%91%E5%B1%9E%EF%BC%8C%E9%93%9D.mp4"
          },
          {
            "id": "video-10",
            "title": "铝",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB1%EF%BC%9A%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99/%E9%9B%95%E5%88%BB%E6%9D%90%E6%96%99%EF%BC%88%E9%87%91%E5%B1%9E%EF%BC%89/%E9%93%9D.mp4"
          }
        ]
      }
    ]
  },
  {
    "id": "usecases",
    "name": "Applications",
    "categories": [
      {
        "id": "3d",
        "name": "3D Embossing",
        "desc": "Layered true relief",
        "videos": [
          {
            "id": "3d-embossing-a-brass-coin-with-the-laserpecker-l",
            "title": "3D_Embossing_a_Brass_Coin_with_the_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/3D%E5%88%BB%E5%8D%B0/3D_Embossing_a_Brass_Coin_with_the_LaserPecker_LP5.mp4"
          },
          {
            "id": "fast-engraving-on-the-switch-with-laserpecker-lp",
            "title": "Fast_engraving_on_the_switch_with_LaserPecker_LP2",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/3D%E5%88%BB%E5%8D%B0/Fast_engraving_on_the_switch_with_LaserPecker_LP2.mp4"
          },
          {
            "id": "stone-3d-embossing-with-laserpecker-lp5-1",
            "title": "Stone_3D_Embossing_with_LaserPecker_LP5 (1)",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/3D%E5%88%BB%E5%8D%B0/Stone_3D_Embossing_with_LaserPecker_LP5%20(1).mp4"
          }
        ]
      },
      {
        "id": "logo",
        "name": "Logo",
        "desc": "Branding in seconds",
        "videos": [
          {
            "id": "color-engraving-with-laserpecker-lp4",
            "title": "Color_Engraving_with_LaserPecker_LP4",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/logo%E5%88%BB%E5%8D%B0/Color_Engraving_with_LaserPecker_LP4.mp4"
          },
          {
            "id": "create-stamp-with-laserpecker-lp5",
            "title": "Create_Stamp_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/logo%E5%88%BB%E5%8D%B0/Create_Stamp_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "done-in-just-10-seconds-laser-engraving-on-towel",
            "title": "Done_in_Just_10_Seconds_Laser_Engraving_on_Towel_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/logo%E5%88%BB%E5%8D%B0/Done_in_Just_10_Seconds_Laser_Engraving_on_Towel_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "laserpecker-lp1-plus-in-action-fully-upgraded-st",
            "title": "LaserPecker_LP1_Plus_in_Action_Fully_Upgraded_Still_Portable",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/logo%E5%88%BB%E5%8D%B0/LaserPecker_LP1_Plus_in_Action_Fully_Upgraded_Still_Portable.mp4"
          },
          {
            "id": "personalize-towels-with-the-laserpecker-lp4-fast",
            "title": "Personalize_Towels_with_the_LaserPecker_LP4_-_Fast_Easy",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/logo%E5%88%BB%E5%8D%B0/Personalize_Towels_with_the_LaserPecker_LP4_-_Fast_Easy.mp4"
          },
          {
            "id": "video-5",
            "title": "金属，铝",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/logo%E5%88%BB%E5%8D%B0/%E9%87%91%E5%B1%9E%EF%BC%8C%E9%93%9D.mp4"
          }
        ]
      },
      {
        "id": "video-2",
        "name": "Tumblers",
        "desc": "Your mark, your cup",
        "videos": [
          {
            "id": "custom-new-year-theme-turnbler-with-laserpecker-",
            "title": "Custom_New_Year_Theme_Turnbler_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E6%9D%AF%E5%AD%90%E6%94%B9%E9%80%A0/Custom_New_Year_Theme_Turnbler_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "customized-coffee-jar-with-laserpecker-lp5",
            "title": "Customized_Coffee_Jar_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E6%9D%AF%E5%AD%90%E6%94%B9%E9%80%A0/Customized_Coffee_Jar_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "glass-engraving-with-laserpecker-lp4-and-rotary-",
            "title": "Glass_engraving_with_LaserPecker_LP4_and_rotary_tool",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E6%9D%AF%E5%AD%90%E6%94%B9%E9%80%A0/Glass_engraving_with_LaserPecker_LP4_and_rotary_tool.mp4"
          },
          {
            "id": "laserpecker-2-custom-engraved-tumbler-diy-engrav",
            "title": "LaserPecker_2_-_custom_engraved_Tumbler._DiY_engraving_full_review_coming_soon",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E6%9D%AF%E5%AD%90%E6%94%B9%E9%80%A0/LaserPecker_2_-_custom_engraved_Tumbler._DiY_engraving_full_review_coming_soon.mp4"
          },
          {
            "id": "laserpecker-lp2-plus-diy-halloween-cup-that-glow",
            "title": "LaserPecker_LP2_Plus_-_DIY_Halloween_Cup_That_Glows",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E6%9D%AF%E5%AD%90%E6%94%B9%E9%80%A0/LaserPecker_LP2_Plus_-_DIY_Halloween_Cup_That_Glows.mp4"
          }
        ]
      },
      {
        "id": "video-3",
        "name": "Gifts",
        "desc": "One-of-a-kind gifts",
        "videos": [
          {
            "id": "back-to-school-shopping-list-but-make-it-persona",
            "title": "Back_to_school_shopping_list_but_make_it_personal._laserpecker_schoolsupplies",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E7%A4%BC%E5%93%81%E5%AE%9A%E5%88%B6/Back_to_school_shopping_list_but_make_it_personal._laserpecker_schoolsupplies.mp4"
          },
          {
            "id": "laser-engraved-football-field-snack-board-with-l",
            "title": "Laser_Engraved_Football_Field_Snack_Board_with_LaserPecker_LX2",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E7%A4%BC%E5%93%81%E5%AE%9A%E5%88%B6/Laser_Engraved_Football_Field_Snack_Board_with_LaserPecker_LX2.mp4"
          },
          {
            "id": "laserpecker-2-lasercut-laserengraving-lasermachi",
            "title": "Laserpecker_2_lasercut_laserengraving_lasermachine_leathercraft_onsitesouvenir_smallbusiness",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E7%A4%BC%E5%93%81%E5%AE%9A%E5%88%B6/Laserpecker_2_lasercut_laserengraving_lasermachine_leathercraft_onsitesouvenir_smallbusiness.mp4"
          },
          {
            "id": "the-best-gift-says-we-thought-of-you-engraved-by",
            "title": "The_best_gift_says_we_thought_of_you._Engraved_by_LP4._backtoschool_laserpecker_giftideas",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E7%A4%BC%E5%93%81%E5%AE%9A%E5%88%B6/The_best_gift_says_we_thought_of_you._Engraved_by_LP4._backtoschool_laserpecker_giftideas.mp4"
          },
          {
            "id": "video-4",
            "title": "材料（塑料）",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E7%A4%BC%E5%93%81%E5%AE%9A%E5%88%B6/%E6%9D%90%E6%96%99%EF%BC%88%E5%A1%91%E6%96%99%EF%BC%89.mp4"
          },
          {
            "id": "video-5",
            "title": "铝",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E7%A4%BC%E5%93%81%E5%AE%9A%E5%88%B6/%E9%93%9D.mp4"
          }
        ]
      },
      {
        "id": "video-4",
        "name": "Apparel",
        "desc": "Custom wearables",
        "videos": [
          {
            "id": "create-one-of-a-kind-clothes-with-laserpecker-lp",
            "title": "Create_One-of-a-Kind_Clothes_with_LaserPecker_LP4",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E8%A1%A3%E6%9C%8D%E3%80%81%E9%A5%B0%E5%93%81%E5%AE%9A%E5%88%B6/Create_One-of-a-Kind_Clothes_with_LaserPecker_LP4.mp4"
          },
          {
            "id": "deep-engraved-buttons-with-laserpecker-lp5",
            "title": "Deep-engraved_Buttons_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E8%A1%A3%E6%9C%8D%E3%80%81%E9%A5%B0%E5%93%81%E5%AE%9A%E5%88%B6/Deep-engraved_Buttons_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "engraving-with-the-laser-pecker-4",
            "title": "Engraving_with_the_Laser_Pecker_4",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E8%A1%A3%E6%9C%8D%E3%80%81%E9%A5%B0%E5%93%81%E5%AE%9A%E5%88%B6/Engraving_with_the_Laser_Pecker_4.mp4"
          },
          {
            "id": "statue-of-liberty-coin-embossing-with-laserpecke",
            "title": "Statue_of_Liberty_Coin_Embossing_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E8%A1%A3%E6%9C%8D%E3%80%81%E9%A5%B0%E5%93%81%E5%AE%9A%E5%88%B6/Statue_of_Liberty_Coin_Embossing_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "turn-your-favorite-photo-into-embossed-artwork-w",
            "title": "Turn_Your_Favorite_Photo_into_Embossed_Artwork_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E8%A1%A3%E6%9C%8D%E3%80%81%E9%A5%B0%E5%93%81%E5%AE%9A%E5%88%B6/Turn_Your_Favorite_Photo_into_Embossed_Artwork_with_LaserPecker_LP5.mp4"
          },
          {
            "id": "video-5",
            "title": "材料（布料）",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E8%A1%A3%E6%9C%8D%E3%80%81%E9%A5%B0%E5%93%81%E5%AE%9A%E5%88%B6/%E6%9D%90%E6%96%99%EF%BC%88%E5%B8%83%E6%96%99%EF%BC%89.mp4"
          }
        ]
      },
      {
        "id": "video-5",
        "name": "Shoes",
        "desc": "Step up your style",
        "videos": [
          {
            "id": "personalize-shoes-with-laserpecker-lp5",
            "title": "Personalize_Shoes_with_LaserPecker_LP5",
            "url": "/videos/laserpeck/%E5%88%86%E7%B1%BB2%EF%BC%9A%E4%BD%BF%E7%94%A8%E5%9C%BA%E6%99%AF/%E9%9E%8B%E7%B1%BB%E5%88%BB%E5%8D%B0/Personalize_Shoes_with_LaserPecker_LP5.mp4"
          }
        ]
      }
    ]
  }
]
