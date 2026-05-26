/* ─── Single Origin Society · Frontend ─── */

/* HTMX loading indicator */
document.addEventListener('DOMContentLoaded', function() {
  /* Smooth page entrance */
  document.body.style.opacity = '0';
  document.body.style.transition = 'opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
  requestAnimationFrame(function() {
    document.body.style.opacity = '1';
  });
});
