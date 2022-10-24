<template>
    <fragment>

        <!-- Use inside of a v-row -->

        <v-col v-if="index !== null" sl>
            <v-select label="Filter by KP"
                    v-model="kp_filter"
                    multiple
                    :items="index.KP"/>
        </v-col>
        <v-col v-if="index !== null" sl>
            <v-select label="Filter by ARA"
                    v-model="ara_filter"
                    multiple
                    :items="Object.keys(index.ARA)"/>
        </v-col>

        <v-col v-if="subject_categories.length > 0" sl>
            <v-select label="Filter subject categories"
                    multiple
                    :items="subject_categories"
                    v-model="subject_category_filter"/>
        </v-col>
        <v-col v-if="predicates.length > 0" sl>
            <v-select label="Filter predicates"
                    multiple
                    :items="predicates"
                    v-model="predicate_filter"/>
        </v-col>
        <v-col v-if="object_categories.length > 0" sl>
            <v-select label="Filter object categories"
                    multiple
                    :items="object_categories"
                    v-model="object_category_filter"/>
        </v-col>

    </fragment>
</template>
<script>
import { Fragment } from 'vue-frag'
export default {
    components: {
        Fragment
    },
    name: 'TranslatorFilter',
    props: ['index', 'subject_categories', 'predicates', 'object_categories'],
    data() {
        return {
            ara_filter: [],        
            kp_filter: [],
            subject_category_filter: [],
            predicate_filter: [],
            object_category_filter: [],
        }
    },
    watch: {
        ara_filter(new_state) {
            this.handleChange('ara_filter', new_state)
        },
        kp_filter(new_state) {
            this.handleChange('kp_filter', new_state)
        },
        subject_category_filter(new_state) {
            this.handleChange('subject_category_filter', new_state)
        },
        predicate_filter(new_state) {
            this.handleChange('predicate_filter', new_state)
        },
        object_category_filter(new_state) {
            this.handleChange('object_category_filter', new_state)
        }
    },
    methods: {
        handleChange(state_name, new_state) {
            return this.$emit(`${state_name}`, new_state)
        }
    }
}
</script>
