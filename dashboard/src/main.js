// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'

import vuejsStorage from 'vuejs-storage';

// autoload plugins
import vuetify from './plugins/vuetify'

import App from './App'

import { Laue } from 'laue'
import VcPiechart from 'vc-piechart'
import 'vc-piechart/dist/lib/vc-piechart.min.css'

Vue.use(vuejsStorage)
Vue.use(Laue)
Vue.use(VcPiechart)

Vue.config.productionTip = false

/* eslint-disable no-new */
new Vue({
  el: '#app',
  vuetify,
  components: { App },
  template: '<App/>'
})
