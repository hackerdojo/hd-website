Technical notes:

The Dojo Website CMS is extremely simple (less than 100 lines of code), but offers some really slick performance tricks:

  * The content is pulled from a PBworks wiki, and cached aggressively.  When a page is edited on the wiki, a webhook is fired from PBworks to the App Engine app with the specific purpose of clearing the cache key.  This hyper efficient design means the app can serve pages from memory with a PERFECT cache efficiency, yet magically updates from the wiki appear _realtime_ on the website.

  * The main HTML is served from app engine, but every other asset (js, css, images, etc) are served from a CDN.  The cdn is located at http://cdn.hackerdojo.com/static and simply mirrors everything from the website on a pull basis.  The CDN also uses gzip compression on appropriate files.  (I'm paying for the CDN personally, it is cheap and one I have used for years and trust.)

  * All JS and CSS have been optimized and packed into one file each.  (And only the index page requires Javascript, to animate the hero image.)

  * The JS and CSS will be cached by the CDN, so the URLs are versioned automatically by App Engine.  Deploying a new version automatically increments the version.

  * HTML is space-optimized .. view source on it ;)

  * When debugging locally, the CDN and wiki cache are disabled.
  
